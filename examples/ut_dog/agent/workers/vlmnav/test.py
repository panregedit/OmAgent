import os
import base64
import requests
import glob
from PIL import Image
import io
import time
def test_action_proposal_api(
    api_url="http://localhost:8075/generate_action_proposals",
    image_pattern=".MVIMG_*",
    output_dir="./output/",
    min_angle=40,
    number_size=30,
    min_path_length=200
):
    """
    Test the action proposal API by sending local images and saving the results.
    
    Args:
        api_url: URL of the API endpoint
        image_pattern: Glob pattern to find input images
        output_dir: Directory to save output images
        min_angle: Minimum angle between proposals
        number_size: Size of the number markers
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all matching image files
    image_files = glob.glob(image_pattern)
    print(f"Found {len(image_files)} images matching pattern '{image_pattern}'")
    
    if not image_files:
        print("No images found. Please check the pattern.")
        return
    
    for image_path in image_files:
        # Get filename without path
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_dir, filename)
        
        print(f"Processing {filename}...")
        
        try:
            # Read image and convert to base64
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Prepare request payload
            payload = {
                "image": image_base64,
                "min_angle": min_angle,
                "number_size": number_size,
                "min_path_length": min_path_length
            }
            
            # Send request to API
            response = requests.post(api_url, json=payload, timeout=60)
            
            if response.status_code == 200:
                # Get response data
                data = response.json()
                output_base64 = data["image"]
                actions = data["actions"]
                
                # Decode base64 image
                output_bytes = base64.b64decode(output_base64)
                
                # Save output image
                with open(output_path, "wb") as f:
                    f.write(output_bytes)
                
                print(f"✓ Saved output to {output_path}")
                print(f"  Actions: {actions}")
            else:
                print(f"✗ Error: API returned status code {response.status_code}")
                print(f"  Response: {response.text}")
        
        except Exception as e:
            print(f"✗ Error processing {filename}: {str(e)}")
    
    print("Processing complete!")

if __name__ == "__main__":
    # You can customize these parameters if needed
    API_URL = "http://10.8.25.28:8075/generate_action_proposals"
    IMAGE_PATTERN = "./MVIMG_*"  # Pattern to match input images
    OUTPUT_DIR = "./output/"
    MIN_ANGLE = 30
    NUMBER_SIZE = 30
    MIN_PATH_LENGTH = 200
    
    #iterate all images in the current directory
    for image_path in glob.glob(IMAGE_PATTERN):
        print(f"Processing {image_path}...")
        start_time = time.time()
        test_action_proposal_api(
            api_url=API_URL,
            image_pattern=image_path,
            output_dir=OUTPUT_DIR,
            min_angle=MIN_ANGLE,
            number_size=NUMBER_SIZE,
            min_path_length=MIN_PATH_LENGTH
        ) 
        end_time = time.time()
        print(f"Time taken: {end_time - start_time} seconds")