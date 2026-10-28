def check_period(period: int, name: str = "period") -> None:
    if not isinstance(period, int) or period <= 0:
        raise ValueError(f"{name} must be a positive integer")
