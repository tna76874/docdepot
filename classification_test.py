#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST
"""
from helper import *
from classify import *
import shutil
import argparse

def main(test_dir):
    # Check if the test_dir exists
    if not os.path.exists(test_dir):
        print(f"Das Verzeichnis {test_dir} existiert nicht.")
        return
    
    classifier = ImageClassifier(url='http://localhost:5500', api_key='test', threshold=0.55)
    
    # Recursively find all files in the test_dir directory
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            # Process each file using the classifier
            file_path = os.path.join(root, file)
            loaded_file = FileLoader(file_path, filename=os.path.basename(file)).load()
            result = classifier.classify_image(loaded_file.buffer)
            
            # Print the result
            if result:
                prediction = result.get('prediction')
                new_file_path = f'/tmp/classify/{int(prediction*100):02d}_{file}'
                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                shutil.copy(file_path, new_file_path)
                print(f'{file} prediction: {prediction}')
            else:
                print(f'Kein Ergebnis für {file}')
                
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process images in a directory.')
    parser.add_argument('test_dir', type=str, help='The directory containing the images to classify')
    
    args = parser.parse_args()
    main(args.test_dir)