<p align="center">❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗<br>
This is the original version of the Videohasher Node script.<br>
I have been working on (Ok...  Claude) a new version that incorporates:<br>
VAAPI, NVENC, Marker generation, API Key, standalone generation for items, etc.<br>
It is currently in testing, but seems to be working well enough. <br>
It is at <a href="https://github.com/Darklyter/StashVideohasherNodeVAAPI">StashVideohasherNodeVAAPI</a><br><br>
I apologize for the names of these things...  I am neither creative nor imaginative.  I also like vanilla ice cream if that gives you an idea.<br>
❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗❗</p>



# 📼 StashVideohasherNode Script

This is a lightweight script designed to distribute the processing of large Stash scene imports across multiple systems. Instead of burdening the Stash server with tasks like cover generation, scrubber sprite creation, preview video rendering, and perceptual hash (phash) computation, this script enables multiple nodes to contribute those tasks back to the server.

## ⚙️ Requirements

- [Peolic's videohashes binaries](https://github.com/peolic/videohashes)  
  Download the appropriate version for your system and update `config.py` with the correct path and filename.

## 🧠 How It Works

- Processes scenes in batches of **25 per node**
- Tags batches as `"In Process"` to prevent duplication
- Continues processing until fewer than 25 scenes remain
- Scenes are selected based on **missing phash**
- If phash is generated but other tasks fail (e.g., cover image), the scene won't be reprocessed

## 💬 Support

The script is well-commented. For questions, reach out via Discord (if you know this script, you probably know how to find me there).
Also one quick note, the file hashes created are OSHASH.  If you currently have your Stash instance set for MD5, these will not be compatible

## 🛠️ CLI Options

You can run the script with the following options, all of which can also be set in `config.py`:

```bash
usage: phash_videohasher_main.py [-h] [--windows] [--generate-sprite] [--generate-preview]
                                 [--batch-size BATCH_SIZE] [--max-workers MAX_WORKERS]
                                 [--dry-run] [--verbose] [--once]

Stash Scene Processor CLI

options:
  -h, --help              Show this help message and exit
  --windows               Use Windows-style paths and binaries
  --generate-sprite       Enable sprite image generation
  --generate-preview      Enable preview video generation
  --batch-size BATCH_SIZE Number of scenes to process per run (default: 25)
  --max-workers MAX_WORKERS Number of threads for parallel processing (default: 4)
  --dry-run               Simulate processing without writing changes
  --verbose               Enable detailed output and progress bars
  --once                  Run a single batch and exit
