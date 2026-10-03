class BackendServiceError(RuntimeError):
    """Base exception for backend service failures."""


class ModelArtifactError(BackendServiceError):
    """Raised when a required model artifact cannot be loaded."""


class ModelFeatureError(BackendServiceError):
    """Raised when model input features are missing or invalid."""


class ModelInferenceError(BackendServiceError):
    """Raised when model inference fails."""


class ThresholdConfigurationError(BackendServiceError):
    """Raised when the configured decision threshold is invalid."""


class WeatherServiceError(BackendServiceError):
    """Raised when weather evidence cannot be retrieved or understood."""