def post_worker_init(worker):
    from sportbit_webapp import (
        voer_scheduler_bij_start_uit,
    )

    voer_scheduler_bij_start_uit()
