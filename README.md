StashVideohasherNode script

This is a very simple script that can be run on multiple systems to process a large Stash import of scenes.  Instead of running cover, scrubber sprite, preview and phash generation tasks on the Stash server itself, this script will allow you to do the same thing on as many computers as you would like, with all of the nodes contributing back to the Stash server.

It requires Peolic's videohashes binaries (https://github.com/peolic/videohashes).  Just download whichever version you need for your system, then update the config.py script to reflect the path and filename that you saved the binaries with.

The script is pretty well commented, but if you have any questions you can message me on Discord.  If you know about this script, you know how to get me on there.  

It will process the queue in batches of 25 scenes per node, and tag that batch as "In Process" to keep other nodes from working on the same scenes.  As it finishes the scenes, it will keep going until there are less than 25 scenes left to be done.  Pretty simple actually.

Also please note, the script will pull scenes to process based on the lack of a phash.  So if you have a phash attached to a scene, the script won't load it for processing the other items.  Likewise the phash is the first thing generated, so if there is a failure on the cover image (for example) then the phash will be written to the scene and it won't be picked up for processing on a subsequent run.

Here is the output from a run with --help to show you the available CLI options (All of which can be set in config.py)

usage: phash_videohasher_main.py [-h] [--windows] [--generate-sprite] [--generate-preview] [--batch-size BATCH_SIZE] [--max-workers MAX_WORKERS] [--dry-run] [--verbose] [--once]

Stash Scene Processor CLI

options:
  -h, --help            show this help message and exit
  --windows             Use Windows-style paths and binaries
  --generate-sprite     Enable sprite image generation
  --generate-preview    Enable preview video generation
  --batch-size BATCH_SIZE
                        Number of scenes to process per run (default: 25)
  --max-workers MAX_WORKERS
                        Number of threads for parallel processing (default: 4)
  --dry-run             Simulate processing without writing changes
  --verbose             Enable detailed output and progress bars
  --once                Run a single batch and exit