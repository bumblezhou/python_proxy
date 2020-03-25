import json
import os
import re
import io
import mimetypes
from requests import Request, Session
from flask import Flask, jsonify, render_template, request
from flask.helpers import send_file

import settings


# https://flask.palletsprojects.com/en/1.1.x/quickstart/#static-files
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/<path:sub_path>', methods=["POST", "GET"])
def sub_path(sub_path):
    target_data = None
    target_header = None
    target_method = request.method

    if(request.data):
        request_data = request.data.decode("utf-8")
        target_body = request_data
        target_header = request.headers

        if isinstance(target_body, str):
            target_data = target_body
        elif isinstance(target_body, dict):
            target_data = json.dumps(target_body)
        else:
            raise Exception('Invalid request body')

    current_target_url = request.referrer.replace("http://localhost:5000/proxy/", "")
    target_url = current_target_url + request.headers.environ["REQUEST_URI"]

    session = Session()

    req = Request(target_method, target_url, data=target_data, headers=target_header)
    prepped = req.prepare()
    # after request print status code and body
    resp = session.send(prepped, timeout=300)

    if request.method == "POST":
        return jsonify({"result": True, "data": resp.text})
    else:
        mime_type = get_mime_type(target_url)
        if (mime_type and mime_type.startswith("image")) or request.headers.environ["HTTP_ACCEPT"].startswith("image"):
            return send_file(
                io.BytesIO(resp.content),
                mimetype=mime_type,
                as_attachment=True,
                attachment_filename=os.path.basename(target_url))
        else:
            return resp.content


def get_mime_type(src):
    file_ext = os.path.splitext(src)[1]
    if "&" in file_ext:
        file_ext = re.sub(r'&(\w+=\w*)+', "", file_ext)
    if file_ext and file_ext.lower() in settings.MIME_DICT:
        return settings.MIME_DICT[file_ext.lower()]
    else:
        return mimetypes.guess_type(src)[0]


@app.route('/proxy/<path:target_url>', methods=["POST", "GET"])
def proxy(target_url):
    target_data = None
    target_header = None
    target_method = None

    if(request.data):
        request_data = request.data.decode("utf-8")
        request_body = json.loads(request_data)

        target_method = request_body["verb"].upper()
        target_header = request_body["header"]
        target_body = request_body["body"]

        if isinstance(target_body, str):
            target_data = target_body
        elif isinstance(target_body, dict):
            target_data = json.dumps(target_body)
        else:
            raise Exception('Invalid request body')
    else:
        target_method = request.method

    session = Session()
    req = Request(target_method, target_url, data=target_data, headers=target_header)
    prepped = req.prepare()
    # after request print status code and body
    resp = session.send(prepped, timeout=300)

    if request.method == "POST":
        return jsonify({"result": True, "data": resp.text})
    else:
        return resp.content


# run the application
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, threaded=True)