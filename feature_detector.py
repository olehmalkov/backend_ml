import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor

import cv2


class FeatureDetector:
    def __init__(self):
        self.ready = False
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def warmup(self):
        """
        Warmup phase to preload any necessary data or configurations.
        Here, it's used to simulate the initialization process.
        """
        await asyncio.sleep(5)
        self.ready = True

    async def process_image(self, image_path):
        """
        Asynchronously process an image to perform feature detection using SIFT.
        """
        if not self.ready:
            raise Exception("Service not ready. Please wait for the warmup to complete.")

        # Offload the CPU-bound operation to a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._detect_features, image_path)
        return result

    def _detect_features(self, image_path):
        """
        Synchronously detect features in an image using SIFT. This method is intended
        to be run in a thread pool.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError("Image file not found.")

        h = 10
        template_window_size = 100
        search_window_size = 50
        # Apply Non-Local Means Denoising
        denoised_image = cv2.fastNlMeansDenoisingColored(image, None, h, h, template_window_size, search_window_size)

        gray = cv2.cvtColor(denoised_image, cv2.COLOR_BGR2GRAY)
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)

        # Process the keypoints and descriptors as needed
        # For simplicity, return the count of keypoints and the shape of descriptors
        result = {
            "keypoints": len(keypoints),
            "descriptors": descriptors.shape if descriptors is not None else (0, 0)
        }

        return result


async def main():
    parser = argparse.ArgumentParser(description='Manually run images in the FeatureDetector')
    parser.add_argument('--image', help='path of the input image', required=True, type=str)
    args = parser.parse_args()

    fd = FeatureDetector()
    print("Warming up")
    await fd.warmup()

    print("Running image")
    result = await fd.process_image(args.image)

    print(f"{result=}")


if __name__ == "__main__":
    asyncio.run(main())

