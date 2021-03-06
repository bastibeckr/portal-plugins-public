Downloadable Link Plugin
---

This Plugin injects a javascript-based control into the Pluto master page, which allows for arbitary shapes
 of any master
 
 - to be transcoded and attached to the item
 - to be automatically uploaded to S3
 - to be downloaded by 3rd party from an emailable link
 
Deployment
--

It's not enough just to install the plugin.  In order to deploy, you must:

- deploy the template provided in the cloudformation/ directory to the Cloudformation console of your AWS account
- once deployed, go to the Outputs tab of the deployed stack. You should see settings for the bucket, key and secret that have been generated
- install the plugin by RPM or by copying the contents to /opt/cantemo/portal/portal/plugins
- update the /opt/cantemo/portal/portal/localsettings.py file:
  
  - set `DOWNLOADABLE_LINK_BUCKET` to the bucket name generated by cloudformation
  - set `DOWNLOADABLE_LINK_KEY` to the access key generated by cloudformation
  - set `DOWNLOADABLE_LINK_SECRET` to the secret key generated by cloudformation
  - set `DOWNLOADABLE_LINK_CHECKINTERVAL` to the time (in seconds) to elapse between runs of the delete-old-files task.  I would recommend that this is no lower than 300 seconds (=5 minutes)
  
Development
---

If you are working on the plugin, as a minimum you need:

- a working Portal installation, either locally or on a VM
- node.js installed, to run the javascript tests.  I'd recommend using `nvm`, the Node Version Manager.
- some of the modules used by Node are not compatible with versions >6 (i.e., 8.x, 9.x at time of writing). I'd recommend using version 6.10 - this is simple enough with `nvm`
- to run the Python tests:
  
  - ensure that you have the requirements in `/test_requirements.txt` installed.  The tests do _not_ require Portal in order to work and don't need to be run in a Portal environment.
  - use the commandline `DJANGO_SETTINGS_MODULE=portal.plugins.gnmdownloadablelink.tests.django_test_settings nosetests -v portal/plugins/gnmdownloadablelink/tests`
  
- to run the Javascript tests:

  - ensure that your Node environment is set up by changing to the plugin directory and running `npm install`, having ensured that you've got a compatible Node version (`nvm list`)
  - run the tests with `npm test`
  
Building RPMs
----

RPMs are automatically built by the CI process, providing that tests pass, using the `/buildrpms.sh` script. You shouldn't need to do this manually.
