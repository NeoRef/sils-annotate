import json, couchdb, os, shortuuid
import time
from flask import render_template, request, make_response, g, abort
from jinja2 import TemplateNotFound
from silsannotate import app

couch = couchdb.Server(url=os.getenv("SILS_CLOUDANT_URL"))

@app.before_request
def set_db():
    g.start_time = time.time()
    db_name = request.args.get("db")

    if "annotationstudy1-2014" == db_name:
        # For the study in 2014, this database should not change; if it does,
        # there is a file called AnnotationStudy1-2014-backup that is a copy of it
        g.db = couch["annotationstudy1-2014"]  
    elif "annotationtest" == db_name:
        g.db = couch["annotationtest"]  
    else:
        # Default to playpen; is also set as environment variable, e.g. os.getenv["SILS_CLOUDANT_DB"]
        g.db = couch["annotationplaypen"]  
    
    g.api_root = "/api"

# @app.teardown_request
# def teardown(exception=None):
#    time_diff = time.time() - g.start_time
#    print "Load time from before request to teardown: {0}".format(time_diff)

@app.errorhandler(500)
def internal_error(exception):
    app.logger.exception(exception)
    return render_template('500.html', 500)

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/<interface_name>/<text_id>')
def show_text(interface_name, text_id):
    try:
        return render_template("{0}/{1}.html".format(interface_name, text_id), dir_prefix=interface_name)
    except TemplateNotFound:
        abort(404, "No page found at this URL. URLs are in the format /<interface_name>/<text_id>?user=username&db=<db_name>.")

@app.route("/store")
def store_root():
    pass

@app.route("/api/search")
def search():
    textId = request.args.get("textId")
    limit = request.args.get("limit")
    # Limit doesn't work quite right here because if you only pull back the first 10 or 20
    # they may be completely at the bottom...is there a way to group or order by document *position*
    # rather than simply ID (which takes into account time, rather than position)???
    # view = g.db.view("main/by_textId", None, limit=limit)
    '''
    "ranges": [                                # list of ranges covered by annotation (usually only one entry)
        {
          "start": "/p[69]/span/span",           # (relative) XPath to start element
          "end": "/p[70]/span/span",             # (relative) XPath to end element
          "startOffset": 0,                      # character offset within start element
          "endOffset": 120                       # character offset within end element
        }
      ],
    order by ranges[0].start?
    '''    
    view = g.db.view("main/by_textId")

    matches = view[textId]
    ret = {
        "total": matches.total_rows,
        "rows": []
    }

    for anno in matches.rows:
        doc = anno["value"]
        doc["id"] = doc["_id"]
        ret["rows"].append(doc)

    resp = make_response(json.dumps(ret, indent=4), 200)
    resp.mimetype = "application/json"
    return resp

@app.route("/api/annotations", methods=["POST"])
def post_new_annotation():
    db_name = request.args.get("db")

    doc = request.json
    doc["_id"] = shortuuid.uuid()

    if "annotationstudy1-2014" != db_name:
        couch_resp = g.db.save(doc)
        resp_object = { "id": couch_resp[0], "_rev": couch_resp[1] }
    else:
        # Do not allow modifying the original annotation study database through the UI
        resp_object = { "id": doc["_id"], "_rev": 1 }

    resp = make_response(json.dumps(resp_object, indent=4), 200)
    resp.mimetype = "application/json"
    return resp
