"""Analysis identity inputs, available without loading numerical libraries."""

ANALYSIS_SR = 22050
HOP = 256
BANDS = ((20, 250), (250, 2000), (2000, 11025))
PARAMETERS = {"sample_rate": ANALYSIS_SR, "hop_length": HOP, "fft_sizes": [512, 2048, 8192],
              "max_duration_s": 600, "onset_min_gap_s": 0.06,
              "onset_prominence": 0.075, "section_min_s": 3.0,
              "object_cosine_threshold": 0.94, "max_objects": 8,
              "object_descriptor": "short_window_positive_spectral_flux",
              "section_descriptor": "band_fractions_and_log_band_power",
              "tempo_autocorrelation": "mean_centered_gaussian_lag_smoothing",
              "pattern_min_phase_coherence": 0.65,
              "feature_normalization": "one_sided_window_energy_power",
              "rhythm_event_channels": "independent_low_mid_high_positive_flux",
              "rhythm_window_s": 4, "rhythm_hop_s": 2,
              "pulse_interval_estimator": "least_squares_integer_cycles_v1",
              "pulse_interval_match_min": 0.7, "pulse_phase_concentration_min": 0.65}
