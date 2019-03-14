Architecture
============

Database
--------

The database of texts and calendars consists of objects serialised into YAML
files and maintained in a git repository.  These are indexable at a sub-file
granularity.

Data server
-----------

The data server does lookups into the database.  This is defined as an
interface; it's anticipated that the first implementation will be a simple
in-process deserialiser and indexer, which will later be made to operate
separately and to expose a REST API so that it can sit behind a caching proxy.

Rite
----

This is the heart of the library.  It generates offices and related material.
The output is a list of renderable objects.  If need be, this could probably be
split into multiple components that operate independently, as for the data
server.

Renderers
---------

These are presentation-layer implementations.  These convert the output of the
rite into some other format for display, e.g. HTML.
