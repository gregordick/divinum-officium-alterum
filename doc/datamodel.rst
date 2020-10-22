Data model
==========

Data in the database is represented as instances of classes in the
`officium.data` package.  These objects are transformed by the program
according to the configured options.

Notes
-----

What are the queries?

Inputs:
 - Date
 - Rubric-set
 - General calendar
 - Local calendar (partially calculated e.g. from patrons?)
 - Potentially lots of specific things (dignity of celebrant, things ad libitum, indults, ...)
 - Which office

How are special-case offices handled?  Somehow we need to work out that _this_ office has different rules from normal.  Probably these should be returned instead of the usual offices in the list of offices for the day.

Pseudocode showing data flow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

>>> # Need to avoid calling everything an "office".
>>> office_map = SomeClassThatMapsCalpointsToOffices()
>>> calendar = Calendar1960(office_map)
>>> # Case in point:
>>> offices = calendar.offices(2020, 4, 21)
>>> offices
[Matins(...), Lauds(...), ...]
>>> # How do we indicate that some offices should be said together?
>>> vespers = offices[n]
>>> list(vespers.render())
[
   Versicle(text='versiculi/deus-in-adjutorium'),
   VersicleResponse(text='versiculi/domine-ad-adjuvandum'),
   Text(text='versiculi/gloria-patri'),
   Text(text='versiculi/sicut-erat'),
   Text(text='versiculi/alleluja'),
]
>>> 

Some thoughts on the above:

 - Golden rule: resolve() until you get a Text (or one of its subclasses), then render().
 - Presentation layer is entirely responsible for line breaks etc.
 - We could subclass the renderable things, and do multiple dispatch in the presentation layer.
 - We probably want some sort of support for recursion, to allow grouping.
 - In fact, we'll definitely want that.  All structure should come of out of rendering layer, to be interpreted (or not) by the presentation layer.
 - Then again, only at the final rendering stage do we want to generate presentable strings, because these must be localised.  This suggests that recursion shouldn't go all the way down.
 - Titles, and any other annotations, are generated in the presentation layer.  Renderable objects could possibly provide some hints.

OK, how about the data-lookup layer?

>>> data_store = DataStore(...?)
>>> data_store.lookup('versiculi', 'domine-ad-adjuvandum')
"Dómine, ad adjuvándum me festína."

 - Templating could be used for commons and suchlike.  The templates would be expanded in the rendering layer.  E.g. ``TemplatedText('commune/doctorum/ad-magnificat', {'N': 'Robérte'})``.


E2E plan
~~~~~~~~

Complete calendar resolution logic
 - 1962
 - others
Magnificat antiphons for August-November
Conclusions to prayers
Triduum
Suffrages
Vespers of the dead
Propers


Building the calendar
~~~~~~~~~~~~~~~~~~~~~

Use do2's calendar.
