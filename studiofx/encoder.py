import platform
import subprocess


def _works(codec):
    cmd = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2:r=30",
           "-c:v", codec, "-f", "null", "-"]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False


def pick_encoder(pref="auto"):
    """auto: prueba AMF (AMD), NVENC (NVIDIA) y cae a x264 (CPU)."""
    if pref != "auto":
        return pref
    for c in ("h264_amf", "h264_nvenc"):
        if _works(c):
            return c
    return "libx264"


def video_args(codec, bitrate="14M"):
    if codec == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "quality", "-b:v", bitrate]
    if codec == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"]


class FFmpegWriter:
    def __init__(self, out, W, H, fps, codec, audio=None):
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", "%dx%d" % (W, H), "-r", str(fps), "-i", "-"]
        if audio:
            cmd += ["-i", audio]
        cmd += video_args(codec, "6M" if H <= 720 else "12M") + ["-pix_fmt", "yuv420p"]
        if audio:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-map", "0:v", "-map", "1:a", "-shortest"]
        cmd += ["-movflags", "+faststart", out]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, frame):
        self.proc.stdin.write(frame.tobytes())

    def close(self):
        self.proc.stdin.close()
        return self.proc.wait()
