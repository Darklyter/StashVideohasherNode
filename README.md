StashVideohasherNode script

This is a very simple script that can be run on multiple systems to process a large Stash import of scenes.  Instead of running cover, scrubber sprite, preview and phash generation tasks on the Stash server itself, this script will allow you to do the same thing on as many computers as you would like, with all of the nodes contributing back to the Stash server.

It requires Peolic's videohashes binaries (https://github.com/peolic/videohashes) that you just need to put into the same directory as this script, then update the script to reflect the filename that you saved the binaries with.

The script is pretty well commented, but if you have any questions you can message me on Discord.  If you know about this script, you know how to get me on there.  

It will process the queue in batches of 25 scenes per node, and tag that batch as "In Process" to keep other nodes from working on the same scenes.  As it finishes the scenes, it will keep going until there are less than 25 scenes left to be done.  Pretty simple actually.