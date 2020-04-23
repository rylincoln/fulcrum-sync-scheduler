# fulcrum-sync-scheduler
sync only specific forms from your fulcrum org on a schedule

create a .env file to hold the private parameters

only tested on node 10.x running on ubuntu 18.04 and postgresql 10.x

a fulcrum app that users can configure app names and app ids in(really just need the app id but that's hard for a person to understand when configuring in Fulcrum front end).

the example fulcrum app json def can be imported into your account if you want to use it.

This configuration allows your Fulcrum users to go add apps to be synced to your Fulcrum Desktop target DB.

Useful for orgs that have a LOT of apps and don't want to sync everything everytime.

## python file
the python file doesn't use fulcrum desktop at all - it's barely tested, but functional.
it currently only syncs the parent level of a form, adds and objectid field, and creates a spatial view

