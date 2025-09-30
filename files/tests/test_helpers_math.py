"""Tests for files/helpers/math.py utility functions."""

from files.helpers.math import remap, clamp, saturate, lerp


def test_remap_basic():
	"""Test basic remap functionality - map from one range to another."""
	# Map 5 from range [0, 10] to range [0, 100]
	result = remap(5, 0, 10, 0, 100)
	assert result == 50


def test_remap_negative_ranges():
	"""Test remap with negative ranges."""
	# Map 0 from range [-10, 10] to range [0, 100]
	result = remap(0, -10, 10, 0, 100)
	assert result == 50


def test_remap_inverted_output():
	"""Test remap with inverted output range."""
	# Map 5 from range [0, 10] to range [100, 0] (inverted)
	result = remap(5, 0, 10, 100, 0)
	assert result == 50


def test_remap_outside_input_range():
	"""Test remap with input outside the source range (extrapolation)."""
	# Map 15 from range [0, 10] to range [0, 100]
	result = remap(15, 0, 10, 0, 100)
	assert result == 150


def test_clamp_within_range():
	"""Test clamp when input is within range."""
	result = clamp(5, 0, 10)
	assert result == 5


def test_clamp_below_min():
	"""Test clamp when input is below minimum."""
	result = clamp(-5, 0, 10)
	assert result == 0


def test_clamp_above_max():
	"""Test clamp when input is above maximum."""
	result = clamp(15, 0, 10)
	assert result == 10


def test_clamp_at_boundaries():
	"""Test clamp when input is exactly at boundaries."""
	assert clamp(0, 0, 10) == 0
	assert clamp(10, 0, 10) == 10


def test_clamp_negative_range():
	"""Test clamp with negative ranges."""
	assert clamp(-5, -10, -1) == -5
	assert clamp(-15, -10, -1) == -10
	assert clamp(0, -10, -1) == -1


def test_saturate_within_range():
	"""Test saturate when input is within [0, 1]."""
	result = saturate(0.5)
	assert result == 0.5


def test_saturate_below_zero():
	"""Test saturate when input is below 0."""
	result = saturate(-0.5)
	assert result == 0


def test_saturate_above_one():
	"""Test saturate when input is above 1."""
	result = saturate(1.5)
	assert result == 1


def test_saturate_at_boundaries():
	"""Test saturate when input is exactly at boundaries."""
	assert saturate(0) == 0
	assert saturate(1) == 1


def test_lerp_basic():
	"""Test basic linear interpolation."""
	# Lerp between 0 and 100 at t=0.5
	result = lerp(0, 100, 0.5)
	assert result == 50


def test_lerp_at_boundaries():
	"""Test lerp at t=0 and t=1."""
	assert lerp(0, 100, 0) == 0
	assert lerp(0, 100, 1) == 100


def test_lerp_negative_values():
	"""Test lerp with negative values."""
	result = lerp(-100, 100, 0.5)
	assert result == 0


def test_lerp_outside_t_range():
	"""Test lerp with t outside [0, 1] (extrapolation)."""
	result = lerp(0, 100, 1.5)
	assert result == 150

	result = lerp(0, 100, -0.5)
	assert result == -50