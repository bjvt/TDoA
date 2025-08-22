#!/usr/bin/env python3
"""
PPS-WAV Alignment Analysis Tool
Analyzes timing precision between PPS pulses and WAV file samples
"""
import json
import numpy as np
import wave
from pathlib import Path
from datetime import datetime, timezone
import matplotlib.pyplot as plt

def load_wav_file(wav_path):
    """Load WAV file and return sample data with timing info."""
    with wave.open(str(wav_path), 'rb') as wav:
        frames = wav.readframes(wav.getnframes())
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        n_frames = wav.getnframes()
    
    # Convert to numpy array
    if sample_width == 2:  # 16-bit
        samples = np.frombuffer(frames, dtype=np.int16)
    elif sample_width == 4:  # 32-bit
        samples = np.frombuffer(frames, dtype=np.int32)
    else:
        raise ValueError(f"Unsupported sample width: {sample_width}")
    
    # Handle multi-channel (though your setup is mono)
    if channels > 1:
        samples = samples.reshape(-1, channels)
    
    return {
        'samples': samples,
        'sample_rate': sample_rate,
        'channels': channels,
        'duration_s': n_frames / sample_rate,
        'n_samples': len(samples),
        'sample_width_bytes': sample_width
    }

def load_metadata(json_path):
    """Load JSON metadata file."""
    with open(json_path, 'r') as f:
        return json.load(f)

def calculate_sample_timestamps(wav_info, start_utc_iso):
    """Calculate UTC timestamp for each sample in the WAV file."""
    start_utc = datetime.fromisoformat(start_utc_iso.replace('Z', '+00:00'))
    start_timestamp = start_utc.timestamp()
    
    # Create timestamp array for each sample
    sample_times = np.arange(wav_info['n_samples']) / wav_info['sample_rate']
    sample_timestamps = start_timestamp + sample_times
    
    return sample_timestamps

def find_pps_alignment(metadata, wav_info):
    """
    Analyze PPS timing alignment with WAV samples.
    Returns alignment analysis with nanosecond precision.
    """
    if 'pps_timing' not in metadata:
        return None
    
    pps_info = metadata['pps_timing']
    
    # Get key timestamps
    pps_utc = pps_info['pps_utc_timestamp']  # PPS pulse time (UTC)
    recording_start = datetime.fromisoformat(metadata['utc_start'].replace('Z', '+00:00')).timestamp()
    sample_rate = wav_info['sample_rate']
    
    # Calculate time offset from PPS to recording start
    pps_to_start_offset = recording_start - pps_utc
    
    # Convert to sample indices
    samples_per_second = sample_rate
    pps_offset_samples = pps_to_start_offset * samples_per_second
    
    # Find the exact sample that corresponds to the PPS pulse
    if pps_offset_samples < 0:
        # PPS happened after recording started
        pps_sample_index = int(abs(pps_offset_samples))
        pps_within_recording = True
    else:
        # PPS happened before recording started
        pps_sample_index = 0  # PPS was before first sample
        pps_within_recording = False
    
    # Calculate nanosecond precision timing
    sample_period_ns = 1e9 / sample_rate  # nanoseconds per sample
    pps_offset_ns = pps_to_start_offset * 1e9  # offset in nanoseconds
    
    # Find fractional sample alignment
    fractional_sample = pps_offset_samples - int(pps_offset_samples)
    fractional_offset_ns = fractional_sample * sample_period_ns
    
    return {
        'pps_utc_timestamp': pps_utc,
        'recording_start_timestamp': recording_start,
        'pps_to_start_offset_s': pps_to_start_offset,
        'pps_to_start_offset_ns': pps_offset_ns,
        'pps_sample_index': pps_sample_index,
        'pps_within_recording': pps_within_recording,
        'sample_rate_hz': sample_rate,
        'sample_period_ns': sample_period_ns,
        'fractional_sample_offset': fractional_sample,
        'fractional_offset_ns': fractional_offset_ns,
        'system_clock_offset_ms': pps_info.get('clock_offset_ms', 0),
        'alignment_precision_ns': abs(fractional_offset_ns)
    }

def create_timing_report(wav_path, json_path):
    """Create comprehensive timing alignment report."""
    
    print(f"\n🎙️  PPS-WAV Alignment Analysis")
    print(f"=" * 50)
    print(f"WAV File: {wav_path.name}")
    print(f"JSON File: {json_path.name}")
    
    # Load data
    try:
        wav_info = load_wav_file(wav_path)
        metadata = load_metadata(json_path)
    except Exception as e:
        print(f"❌ Error loading files: {e}")
        return None
    
    print(f"\n📊 Recording Info:")
    print(f"  Duration: {wav_info['duration_s']:.3f} seconds ({wav_info['duration_s']/60:.2f} minutes)")
    print(f"  Sample Rate: {wav_info['sample_rate']:,} Hz")
    print(f"  Samples: {wav_info['n_samples']:,}")
    print(f"  Channels: {wav_info['channels']}")
    print(f"  File Size: {wav_path.stat().st_size:,} bytes")
    
    # Analyze PPS alignment
    alignment = find_pps_alignment(metadata, wav_info)
    
    if alignment is None:
        print(f"\n❌ No PPS timing data found in JSON file")
        return None
    
    print(f"\n🕐 Timing Analysis:")
    print(f"  PPS Timestamp (UTC): {datetime.fromtimestamp(alignment['pps_utc_timestamp'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}Z")
    print(f"  Recording Start (UTC): {datetime.fromtimestamp(alignment['recording_start_timestamp'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}Z")
    print(f"  PPS to Start Offset: {alignment['pps_to_start_offset_s']:.9f} seconds")
    print(f"  PPS to Start Offset: {alignment['pps_to_start_offset_ns']:.0f} nanoseconds")
    
    print(f"\n🎯 Sample Alignment:")
    print(f"  Sample Period: {alignment['sample_period_ns']:.1f} ns/sample")
    print(f"  PPS Sample Index: {alignment['pps_sample_index']:,}")
    print(f"  PPS Within Recording: {'✅ Yes' if alignment['pps_within_recording'] else '❌ No'}")
    print(f"  Fractional Sample: {alignment['fractional_sample_offset']:.6f}")
    print(f"  Fractional Offset: {alignment['fractional_offset_ns']:.1f} ns")
    
    print(f"\n📏 Precision Metrics:")
    print(f"  System Clock Offset: {alignment['system_clock_offset_ms']:.1f} ms")
    print(f"  Alignment Precision: {alignment['alignment_precision_ns']:.1f} ns")
    
    # Precision rating
    if alignment['alignment_precision_ns'] < 1000:
        precision_rating = "🟢 EXCELLENT (sub-microsecond)"
    elif alignment['alignment_precision_ns'] < 10000:
        precision_rating = "🟡 GOOD (microsecond-level)"
    elif alignment['alignment_precision_ns'] < 100000:
        precision_rating = "🟠 FAIR (10s of microseconds)"
    else:
        precision_rating = "🔴 POOR (>100μs)"
    
    print(f"  Precision Rating: {precision_rating}")
    
    return alignment

def analyze_multiple_files(base_dir):
    """Analyze all WAV/JSON pairs in a directory."""
    base_path = Path(base_dir)
    wav_files = list(base_path.glob("NFC_*.wav"))
    
    if not wav_files:
        print(f"No NFC WAV files found in {base_dir}")
        return
    
    print(f"\n🔍 Found {len(wav_files)} WAV files to analyze")
    alignments = []
    
    for wav_file in sorted(wav_files):
        json_file = wav_file.with_suffix('.json')
        
        if not json_file.exists():
            print(f"⚠️  Missing JSON file for {wav_file.name}")
            continue
        
        print(f"\n" + "="*60)
        alignment = create_timing_report(wav_file, json_file)
        if alignment:
            alignments.append({
                'file': wav_file.name,
                'alignment': alignment
            })
    
    # Summary statistics
    if alignments:
        precisions = [a['alignment']['alignment_precision_ns'] for a in alignments]
        print(f"\n📈 SUMMARY STATISTICS:")
        print(f"Files Analyzed: {len(alignments)}")
        print(f"Mean Precision: {np.mean(precisions):.1f} ns")
        print(f"Best Precision: {np.min(precisions):.1f} ns")
        print(f"Worst Precision: {np.max(precisions):.1f} ns")
        print(f"Std Deviation: {np.std(precisions):.1f} ns")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} /data/nfc                    # Analyze all files in directory")
        print(f"  {sys.argv[0]} /data/nfc/NFC_20241201T120000Z.wav  # Analyze specific file")
        return 1
    
    path = Path(sys.argv[1])
    
    if path.is_dir():
        analyze_multiple_files(path)
    elif path.is_file() and path.suffix == '.wav':
        json_path = path.with_suffix('.json')
        if not json_path.exists():
            print(f"❌ JSON file not found: {json_path}")
            return 1
        create_timing_report(path, json_path)
    else:
        print(f"❌ Invalid path: {path}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
