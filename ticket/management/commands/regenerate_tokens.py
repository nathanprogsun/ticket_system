import uuid
import time
import threading
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import transaction
from django.db.models import Min, Max
from django.utils import timezone
from ticket.models import Ticket
import sys


class Command(BaseCommand):
    help = "Regenerate ticket tokens using time-based sharding"

    def __init__(self):
        super().__init__()
        self.stop_monitoring = threading.Event()
        self.processed_lock = threading.Lock()
        self.stdout_lock = threading.Lock()
        self.is_resume = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of tickets to process in each batch",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=6,
            help="Number of workers to process tickets in parallel",
        )
        parser.add_argument(
            "--resume", action="store_true", help="Resume from the last saved position"
        )

    def _monitor_progress(self, total_tickets):
        """Monitor and display progress of all workers in real-time"""
        start_time = time.time()
        last_processed = 0
        last_time = start_time

        while not self.stop_monitoring.is_set():
            try:
                time.sleep(0.5)
                current_time = time.time()

                # Get progress data with thread safety
                worker_counts = self._get_worker_counts()
                total_processed = sum(worker_counts.values())

                # Calculate processing speed and ETA
                elapsed = current_time - start_time
                speed = total_processed / elapsed if elapsed > 0 else 0

                # Calculate recent speed for more accurate ETA
                last_processed, last_time = self._calculate_recent_speed(
                    total_processed, last_processed, last_time, current_time
                )

                # Estimate remaining time
                eta_str = self._estimate_remaining_time(
                    total_tickets, total_processed, speed
                )

                # Format worker status string with fixed width
                worker_status = self._format_worker_status(worker_counts)

                # Update progress display in place (without newline)
                self._update_progress_display(
                    total_processed, total_tickets, speed, eta_str, worker_status
                )

            except Exception as e:
                self.stderr.write(f"\nMonitor error: {str(e)}")
                break

    def _get_worker_counts(self):
        """Retrieve processed counts for all workers in a thread-safe manner"""
        with self.processed_lock:
            return {
                i: cache.get(f"worker_{i}_processed_count", 0)
                for i in range(self.worker_count)
            }

    def _calculate_recent_speed(
        self, total_processed, last_processed, last_time, current_time
    ):
        """Calculate recent processing speed for ETA estimation"""
        time_delta = current_time - last_time
        if time_delta >= 1.0:  # Update speed calculation every second
            last_processed = total_processed
            last_time = current_time
        return last_processed, last_time

    def _estimate_remaining_time(self, total_tickets, total_processed, speed):
        """Estimate remaining time for processing tickets"""
        remaining_items = total_tickets - total_processed
        if speed > 0:
            eta_seconds = remaining_items / speed
            if eta_seconds < 60:
                return f"{eta_seconds:.0f}s"
            elif eta_seconds < 3600:
                return f"{eta_seconds/60:.1f}m"
            else:
                return f"{eta_seconds/3600:.1f}h"
        else:
            return "N/A"

    def _format_worker_status(self, worker_counts):
        """Format the worker status string for display"""
        return " | ".join(
            f"W{i}: {worker_counts[i]:5d}" for i in range(self.worker_count)
        )

    def _update_progress_display(
        self, total_processed, total_tickets, speed, eta_str, worker_status
    ):
        """Update the progress display in the console"""
        sys.stdout.write(
            f"\rProgress: {(total_processed/total_tickets)*100:6.2f}% "
            f"({total_processed:6d}/{total_tickets}) | "
            f"Speed: {speed:8.2f} items/sec | "
            f"ETA: {eta_str:>6} | "
            f"Workers: [{worker_status}]"
        )
        sys.stdout.flush()

    def _process_time_chunk(
        self,
        worker_id,
        batch_size,
        time_boundaries,
    ):
        """Process tickets within a specific time range chunk"""
        total_processed = (
            cache.get(f"worker_{worker_id}_processed_count", 0) if self.is_resume else 0
        )
        last_created_at = (
            cache.get(f"worker_{worker_id}_last_created_at") if self.is_resume else None
        )

        chunk_start, chunk_end = time_boundaries[worker_id]
        processed = 0
        updates = []

        try:
            query = self._get_query_by_timerange(
                chunk_start=chunk_start,
                chunk_end=chunk_end,
            )

            if last_created_at:
                query = query.filter(created_at__gt=last_created_at)

            for ticket in query.order_by("created_at").iterator():
                updates.append(
                    Ticket(
                        id=ticket.id, token=uuid.uuid4().hex, updated_at=timezone.now()
                    )
                )
                processed += 1
                last_created_at = ticket.created_at

                if len(updates) >= batch_size:
                    total_processed = self._bulk_update_tickets(
                        updates, worker_id, total_processed, last_created_at
                    )
                    updates = []
                    time.sleep(0.01)  # Reduced sleep time

            if updates:
                self._bulk_update_tickets(
                    updates, worker_id, total_processed, last_created_at
                )
                total_processed += len(updates)

        except KeyboardInterrupt:
            self._bulk_update_tickets(
                updates, worker_id, total_processed, last_created_at
            )
            raise

        except Exception as e:
            self.stderr.write(f"Worker {worker_id} error: {str(e)}")
            raise

        return total_processed

    def _get_query_by_timerange(self, *, chunk_start, chunk_end):
        return self._get_base_query().filter(
            created_at__gte=chunk_start,
            created_at__lt=chunk_end,
        )

    def _get_base_query(self):
        """Get the base query for tickets within the specified time range"""
        return Ticket.objects.filter(
            order__deleted_at__isnull=True,
            order__user__deleted_at__isnull=True,
            order__user__email__endswith="@example.com",
            # order__user__id="3a1a185b219d412a9ea9f14ab1582065",
        )

    def _bulk_update_tickets(
        self, updates, worker_id, total_processed, last_created_at
    ):
        """Perform bulk update of tickets and update cache"""
        if updates:
            with transaction.atomic():
                Ticket.objects.bulk_update(updates, fields=["token", "updated_at"])
                with self.processed_lock:
                    total_processed += len(updates)
                    cache.set(
                        f"worker_{worker_id}_processed_count", total_processed, 86400
                    )
                    cache.set(
                        f"worker_{worker_id}_last_created_at", last_created_at, 86400
                    )
        return total_processed

    def handle(self, *args, **options):
        self.worker_count = options["workers"]
        batch_size = options["batch_size"]
        resume = options["resume"]

        try:
            # Base query to filter tickets
            base_query = self._get_base_query()
            total_tickets = base_query.count()
            self.stdout.write(f"Initial count: {total_tickets}")

            if total_tickets == 0:
                self.stdout.write(self.style.SUCCESS("No tickets to process"))
                return

            # Calculate time boundaries
            time_range = base_query.aggregate(
                min_time=Min("created_at"), max_time=Max("created_at")
            )
            min_time = time_range["min_time"]
            max_time = time_range["max_time"]

            # Calculate time chunks
            time_span = (max_time - min_time).total_seconds()
            chunk_seconds = time_span / self.worker_count

            # Calculate time boundaries and store expected counts
            time_boundaries = []
            for worker_id in range(self.worker_count):
                chunk_start = min_time + timedelta(seconds=chunk_seconds * worker_id)
                chunk_end = min_time + timedelta(
                    seconds=chunk_seconds * (worker_id + 1)
                )
                if worker_id == self.worker_count - 1:
                    chunk_end = max_time + timedelta(seconds=1)

                # Calculate expected count for this worker
                expected_count = base_query.filter(
                    created_at__gte=chunk_start, created_at__lt=chunk_end
                ).count()

                self.stdout.write(
                    f"Worker {worker_id} expected count: {expected_count}"
                )
                time_boundaries.append((chunk_start, chunk_end))

                # Store expected count in cache and initialize processed count
                cache.set(f"worker_{worker_id}_expected_count", expected_count, 86400)

            self.stdout.write(
                f"Starting to process {total_tickets} tickets with {self.worker_count} workers"
            )

            # Initialize worker caches based on resume option
            self._initialize_worker_caches(resume)

            # Start progress monitor in the main thread
            monitor_thread = threading.Thread(
                target=self._monitor_progress, args=(total_tickets,)
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            # Process tickets with multiple workers
            with ThreadPoolExecutor(max_workers=self.worker_count) as executor:
                future_to_worker = {
                    executor.submit(
                        self._process_time_chunk,
                        worker_id,
                        batch_size,
                        time_boundaries,
                    ): worker_id
                    for worker_id in range(self.worker_count)
                }

                try:
                    for future in as_completed(future_to_worker):
                        worker_id = future_to_worker[future]
                        try:
                            future.result()
                        except Exception as e:
                            self.stderr.write(
                                f"Worker {worker_id} failed with error: {str(e)}"
                            )
                except KeyboardInterrupt:
                    self.stdout.write("\nGracefully shutting down workers...")
                    self.stop_monitoring.set()  # Signal monitor to stop
                    executor.shutdown(wait=True, cancel_futures=True)

            time.sleep(2)  # Wait for monitor to print the final progress
            # Wait for monitor to finish
            self.stop_monitoring.set()
            monitor_thread.join(timeout=5)

            # Print final statistics with lock
            self.stdout.write("\nFinal processing statistics:")
            with self.processed_lock:
                for worker_id in range(self.worker_count):
                    processed = cache.get(f"worker_{worker_id}_processed_count", 0)
                    expected = cache.get(f"worker_{worker_id}_expected_count", 0)
                    percentage = (processed / expected * 100) if expected > 0 else 0
                    self.stdout.write(
                        f"Worker {worker_id}: {processed} records ({percentage:.1f}% of expected share)"
                    )

        except Exception as e:
            self.stderr.write(f"Command failed: {str(e)}")
            self.stop_monitoring.set()  # Ensure monitor stops
            raise

        self.stdout.write(self.style.SUCCESS("Token regeneration completed"))

    def _initialize_worker_caches(self, resume):
        """Initialize worker caches based on whether resuming or starting fresh"""
        if resume:
            self.stdout.write("Resuming from last saved position...")
            for worker_id in range(self.worker_count):
                self.is_resume = True
                # Retrieve the processed count from cache just for debugging
                # processed_count = cache.get(f"worker_{worker_id}_processed_count", 0)
                # last_created_at = cache.get(f"worker_{worker_id}_last_created_at", None)
                # self.stdout.write(f"Worker {worker_id} has processed {processed_count} tickets.")
                # self.stdout.write(f"Worker {worker_id} last_created_at: {last_created_at}")

        else:
            self.stdout.write("Initializing new processing tracking...")
            for worker_id in range(self.worker_count):
                cache.delete(f"worker_{worker_id}_last_created_at")
                cache.delete(f"worker_{worker_id}_processed_count")
