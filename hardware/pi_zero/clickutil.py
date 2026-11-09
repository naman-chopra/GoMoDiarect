import subprocess
import os


def capture(img_name_jpg):
    print(os.getcwd())
    subprocess.run(
        f"libcamera-jpeg -t 3 --autofocus-mode auto -o {img_name_jpg}", shell=True
    )
    if os.path.exists(img_name_jpg):
        print("Image captured")
        return True
    else:
        print("Failed to capture image")
        return False
