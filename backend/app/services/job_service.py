"""
Job Service - Async Background Job Processing

Handles async generation jobs for long-running operations.
"""
import uuid
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from app.models.schemas import JobStatus


@dataclass
class Job:
    """Represents an async job."""
    job_id: str
    session_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    message: str = ""
    error: Optional[str] = None
    result: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # The async function to execute
    task_func: Optional[Callable] = None
    task_args: tuple = ()
    task_kwargs: dict = field(default_factory=dict)


class JobManager:
    """
    Manages async background jobs.
    
    Provides:
    - Job queuing
    - Status tracking
    - Progress updates
    - Result retrieval
    """
    
    MAX_CONCURRENT_JOBS = 5
    JOB_RETENTION_HOURS = 24
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def create_job(
        self,
        session_id: str,
        job_type: str,
        task_func: Callable,
        *args,
        **kwargs
    ) -> Job:
        """
        Create and queue a new job.
        
        Args:
            session_id: Associated session ID
            job_type: Type of job (e.g., "generate", "update")
            task_func: Async function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            The created Job object
        """
        job_id = str(uuid.uuid4())
        
        # Include session_id in kwargs for the task function
        kwargs['session_id'] = session_id
        
        job = Job(
            job_id=job_id,
            session_id=session_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            message="Job queued",
            task_func=task_func,
            task_args=args,
            task_kwargs=kwargs
        )
        
        self.jobs[job_id] = job
        await self._queue.put(job_id)
        
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def update_job_progress(self, job_id: str, progress: int, message: str = ""):
        """Update job progress."""
        job = self.jobs.get(job_id)
        if job:
            job.progress = progress
            job.message = message
    
    async def process_jobs(self):
        """
        Background job processor.
        
        Continuously processes jobs from the queue.
        """
        self._running = True
        
        while self._running:
            try:
                # Wait for a job with timeout
                try:
                    job_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                job = self.jobs.get(job_id)
                if not job:
                    continue
                
                # Process the job
                await self._execute_job(job)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Job processor error: {e}")
                continue
    
    async def _execute_job(self, job: Job):
        """Execute a single job."""
        job.status = JobStatus.PROCESSING
        job.progress = 0
        job.message = "Processing..."
        
        try:
            if job.task_func:
                result = await job.task_func(
                    *job.task_args,
                    job_id=job.job_id,
                    **job.task_kwargs
                )
                job.result = result
            
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.message = "Completed successfully"
            job.completed_at = datetime.now()
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.message = f"Failed: {str(e)}"
            job.completed_at = datetime.now()
    
    def stop(self):
        """Stop the job processor."""
        self._running = False
    
    def cleanup_old_jobs(self):
        """Remove old completed jobs."""
        now = datetime.now()
        to_remove = []
        
        for job_id, job in self.jobs.items():
            if job.completed_at:
                hours_old = (now - job.completed_at).total_seconds() / 3600
                if hours_old > self.JOB_RETENTION_HOURS:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.jobs[job_id]


# Global job manager instance
job_manager = JobManager()
