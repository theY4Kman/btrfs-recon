# btrfs-recon

A collection of btrfs on-disk structure parsers, which can feed into a Postgres DB, where they can be changed and written back to disk.


# Background

Back in December 2021, I restarted my computer and discovered my btrfs `/home` volume could not be mounted. Not in read-only mode, and not with all rescue options enabled. I immediately imaged the two 1TB drives and threw them on a 4TB HDD I had. Then, I threw the kitchen sink at it, trying any and every btrfs-progs incantation — including dangerous and destructive rescues. Nothing fixed the issue.

But, I could open up the disk images and see all my data. I was even able to pull off some things I considered valuable, like some local infrastructure passwords, or parts of an xfce4 panel plugin I never pushed to github. I ran some disk health checks, but two disks failing at the same exact time was a little crazy.

No, the likeliest issue, I figured, was some sort of corruption or false fsync occurring at an extremely inopportune moment, causing the metadata structures of the btrfs volume to become unreadable. This sort of issue is bound to happen if, for some dumb reason, you chose to stripe your disks with only a single copy of metadata. Don't do this. If you've done this, pause your viewer now and tell btrfs to `dup` your metadata.

I spent the next few months learning _a lot_ about btrfs internals and on-disk structures, hoping to diagnose and repair the underlying issue. The official wiki includes a bunch of useful information about structures. I learned to parse some structures using [ImHex](https://imhex.werwolv.net/), but realized it would not scale to the _entire drive_. I found the [Construct](https://construct.readthedocs.io/en/latest/) Python library for binary structure parsing/writing, and built out a library of parsers for the btrfs structures I cared about.

With my handful of parsers, I built my own scanner to locate btrfs node headers and found lots of juicy bits. Very many lots. Too many to comb through to diagnose effectively (especially during only my free time). What I really wanted was to query all the on-disk structures and their relationships — I wanted to throw everything in a DB (b-trees on b-trees, baby).

I spun up a Postgres DB, whipped up some marshmallow serializers, and farted out a small set of CLI commands to wrap it all together. I then re-scanned the disk images, saving all structures to the DB. This included all the superblocks, all the chunk items (so physical locations could be calculated), all the tree nodes, all the leaf items, and linked rows by foreign key if there were relationships. I learned how to actually use the chunk tree to read striped, non-INLINE, REGULAR file extent items, and could recover arbitrary files.

More importantly, I could try to mount the broken disk, read the errors spit out, and _query for the faulty structure at the logical location_. I could then navigate to parents and children very easily.

After months and months of work and lots and lots of code, I discovered the issue: the chunk tree had to be grown, leading to a new chunk root, but got interrupted before updating the superblocks with the proper logical bytenr. When I shoved the correct `chunk_root` value into the superblocks (along with proper checksums), the volume became mountable.

Months and months, and the fix took not more than 10 minutes.

---

So, if you've got some busted btrfs volume, or are just curious about what's going on under there, you may find the things here useful. At the very least, the on-disk structure parsers may be handy. The DB part, while incredibly vital to me, has no docs for setting up. I would love to polish these things up to a releasable state, but that hasn't happened, yet, and it's been months. Till then, I still want the community to have access to this code.
