import cv2

print("Checking camera devices...")
print()

for camera_index in range(5):

    print(f"Testing camera index {camera_index}...")

    camera = cv2.VideoCapture(
        camera_index,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():

        print("  ❌ Could not open")
        camera.release()
        continue

    success, frame = camera.read()

    if not success:

        print("  ❌ Opened, but could not read frame")
        camera.release()
        continue

    print(
        f"  ✅ Working | "
        f"Shape: {frame.shape} | "
        f"Min: {frame.min()} | "
        f"Max: {frame.max()}"
    )

    cv2.imshow(
        f"Camera Index {camera_index}",
        frame
    )

    print(
        f"  Look at Camera Index {camera_index} window."
    )

    print(
        "  Press any key to test the next camera."
    )

    cv2.waitKey(0)

    camera.release()

    cv2.destroyAllWindows()


print()
print("Camera test finished.")