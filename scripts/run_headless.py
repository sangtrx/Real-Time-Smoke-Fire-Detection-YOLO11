#!/usr/bin/env python3
"""Headless runner: process a video file with the project's Detector and write annotated output.

Usage:
  python scripts/run_headless.py input.mp4 --out detected_fires/out.mp4 --max-frames 300
"""
import argparse
from pathlib import Path
import cv2
import logging
from src.config import Config, setup_logging
from src.fire_detector import Detector


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('input', type=Path, help='Input video path')
    p.add_argument('--out', type=Path, default=Path('detected_fires/out.mp4'), help='Output video path')
    p.add_argument('--max-frames', type=int, default=0, help='Max frames to process (0 = all)')
    p.add_argument('--model', type=Path, default=Config.MODEL_PATH, help='Path to model file')
    return p.parse_args()


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    args = parse_args()
    in_path = args.input
    out_path = args.out
    max_frames = args.max_frames

    if not in_path.exists():
        logger.error(f"Input video not found: {in_path}")
        raise SystemExit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    detector = Detector(args.model)

    cap = cv2.VideoCapture(str(in_path))
    if not cap.isOpened():
        logger.error(f"Failed to open input: {in_path}")
        raise SystemExit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    writer = None
    frame_count = 0

    # We'll write to a temporary container first, then re-encode to H.264 for
    # maximum compatibility using ffmpeg (if available).
    tmp_out = out_path.with_suffix('.tmp.mp4')

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            processed, detection = detector.process_frame(frame)

            # initialize writer using processed frame dimensions
            if writer is None:
                h, w = processed.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(str(tmp_out), fourcc, fps, (w, h))
                if not writer.isOpened():
                    logger.error(f"Failed to open video writer for {tmp_out}")
                    raise SystemExit(1)

            writer.write(processed)

            frame_count += 1
            if max_frames and frame_count >= max_frames:
                break

            if frame_count % 50 == 0:
                logger.info(f"Processed {frame_count} frames")

    finally:
        cap.release()
        if writer:
            writer.release()

    # If ffmpeg is available, re-encode tmp_out to H.264 into the requested out_path
    import shutil
    from subprocess import run

    if tmp_out.exists():
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            logger.info('Re-encoding output to H.264 for compatibility using ffmpeg')
            cmd = [ffmpeg_path, '-y', '-i', str(tmp_out), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', str(out_path)]
            res = run(cmd)
            if res.returncode == 0 and out_path.exists():
                logger.info(f'Re-encode successful. Removing temporary file: {tmp_out}')
                try:
                    tmp_out.unlink()
                except Exception:
                    logger.warning(f'Failed to remove temporary file: {tmp_out}')
            else:
                logger.warning('ffmpeg re-encode failed; leaving temporary file as output')
                # If re-encode failed, move tmp_out to out_path as a fallback
                try:
                    tmp_out.replace(out_path)
                except Exception:
                    logger.error('Failed to move temporary output to final destination')
        else:
            # No ffmpeg: move tmp_out to out_path
            try:
                tmp_out.replace(out_path)
                logger.warning('ffmpeg not found; wrote output in container with mp4v codec')
            except Exception:
                logger.error('Failed to rename temporary output file')

    logger.info(f"Done. Processed {frame_count} frames. Output saved to: {out_path}")


if __name__ == '__main__':
    main()
