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
              "pulse_interval_match_min": 0.7, "pulse_phase_concentration_min": 0.65,
              "beat_tracker": "weighted_spectral_periodicity_dynamic_programming_v1",
              "beat_tempo_range_bpm": [40, 240], "beat_prior_bpm": 120,
              "beat_prior_octave_sd": 0.6, "beat_ac_min": 0.12,
              "beat_score_min": 0.05, "beat_spectral_support_min": 0.1,
              "beat_novelty": "half_mixture_half_normalized_band_mean",
              "beat_local_fallback": "three_coherent_windows_min_60_percent",
              "beat_window_s": 8, "beat_hop_s": 2, "beat_transition_tightness": 30,
              "beat_support_tolerance_s": 0.05}
