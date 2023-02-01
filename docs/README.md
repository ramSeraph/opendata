# Building pages locally
To test the github pages build locally.. run `./pages.sh` from this directory. 

This expects your github token to be present in `token.txt`.

At this point of time I don't remember if the github token is supposed be from the owner of the repository
 and if it requires write scope as well(unlikely).

This will generate the site content into the `_site/` folder.

# Serving pages locally

To check the pages locally, you will need to serve them with a local http server.

This can be done by installing `http-server-subpath` using the `npm i -g http-server-subpath`.

Now run `npx http-server --path opendata _site/` from this folder. this makes the local build at `_site` accessible at http://127.0.0.1:8080/opendata

# generating stripped down turf.js

run the following:
`cd generators`
`./create_turf.sh`
