import os
import pickle
import scraper

def walk():
    for root, dirs, files in os.walk("./failed_payloads"):
        for fName in files:
            with open(os.path.join(root, *dirs, fName), mode="rb") as f:
                try:
                    print(pickle.load(f))
                except Exception as e:
                    print(f"Failed: {e}")

def main():
    with open(os.path.join("./failed_payloads", "data_20251204_121456.pkl"), 'rb') as f:
        try:
            print(pickle.load(f))
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    main()