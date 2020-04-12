const fulcrum = require('fulcrum-app');
const Client = fulcrum.Client;
const log = require('log-to-file');
const shell = require('shelljs');
const schedule = require('node-schedule');
require('dotenv').config()

var form_ids = [];

// setup a fulcrum client
const client = new Client(process.env.TOKEN);

// define an interval for the schedule
var rule = new schedule.RecurrenceRule();
// every Nth minute of every hour
rule.minute = 16;

// trigger the schedule can listen to j for events emitted
var j = schedule.scheduleJob(rule, function () {
    getForms()
});

// get the forms to sync from the fulcrum config app
const getForms = function () {
    // change this to the fulcrum app you've created that must have at least a form_id field in it
    client.query('SELECT form_id FROM "08134861-d511-42ad-949d-ec4db2897434"')
        .then((forms) => {
            console.log(JSON.stringify(forms, 2))
            forms.rows.forEach(row => {
                form_ids.push('--form ' + row.form_id)
            })

            let fulcrum_sync = `cd /opt/Fulcrum/scripts && ./fulcrum sync --org '` + process.env.ORG + `' --pg-schema-views fulcrum_views --pg-user '` + process.env.PGUSER + `' --pg-password '` + process.env.PGPASS + `' --pg-host ` + process.env.PGHOST + ` `

            let cli_forms = form_ids.join(' ');

            let fulcrum_cli = fulcrum_sync + cli_forms;

            // execute the fulcrum desktop sync process
            if (shell.exec(fulcrum_cli).code !== 0) {
                log('Error: Fulcrum Sync failed :(');
                shell.exit(1);
            }
        })
        .catch(() => {
            log('something went wrong in getRecords()');
        });
}
