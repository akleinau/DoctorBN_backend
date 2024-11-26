import datetime
import io
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from random import random

from flask import Flask, request, jsonify, got_request_exception
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

import rollbar
import rollbar.contrib.flask

from py_src.Network import Network
from py_src.Scenario import Scenario

ALLOWED_EXTENSIONS = ['.net']
TEMPLATE_FOLDER = os.path.abspath('./src')
app = Flask(__name__, template_folder=TEMPLATE_FOLDER)
app.config.from_pyfile('settings.py')
# app.config['NETWORK_FOLDER'] = NETWORK_FOLDER
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CORS(app)

with app.app_context():
    """init rollbar module"""
    rollbar.init(
        # access token
        os.environ["ROLLBAR_PROJECT_ACCESS_TOKEN"],
        # environment name - any string, like 'production' or 'development'
        'production',
        # server root directory, makes tracebacks prettier
        root=os.path.dirname(os.path.realpath(__file__)),
        # flask already sets up logging
        allow_logging_basic_config=False)

    # send exceptions from `app` to rollbar, using flask's signal system.
    got_request_exception.connect(rollbar.contrib.flask.report_exception, app)

@app.route('/create_tables')
def create_tables():
    db.create_all()

@app.route('/getNetwork')
def getNetwork():
    data = request
    network = getNetworkInDatabase(data.args.get('network')) #else load from database
    s = Scenario(network.fileString, network.fileFormat)
    return {'states': s.network.states, 'edges': s.network.edges, 'description': network.description,
            'labels': s.network.labels, 'customization': network.customization}


@app.route('/getLocalNetwork', methods=['POST'])
def getLocalNetwork():
    network = request.get_json()
    s = Scenario(network["fileString"], network["fileFormat"])
    return {'states': s.network.states, 'edges': s.network.edges, 'description': network["description"],
            'labels': s.network.labels}

@app.route('/calcTargetForGoals', methods=['POST'])
def calcTargetForGoals():
    data = request.get_json()
    if 'fileString' in data:
        network = data['fileString'] #load the local network directly from user pc
        fileFormat = data["fileFormat"]
    else:
        # else load from database
        DBitem = getNetworkInDatabase(data['network'])
        network = DBitem.fileString
        fileFormat = DBitem.fileFormat
    s = Scenario(network, fileFormat, evidences=data['evidences'], targets=data['target'], goals=data['goals'],
                 goalDirections=data['goalDirections'])
    results = s.compute_target_combs_for_goals()
    likely_results = s.compute_goals()
    return {'optionResults': results, 'likelyResults': likely_results}


#calculates the explanation of the chosen option
@app.route('/calcOptions', methods=['POST'])
def calcOptions():
    #data prep
    data = request.get_json()
    relevanceEvidences = {}
    for ev in data['evidences']:
        relevanceEvidences[ev] = data['evidences'][ev]
    for op in data['options']:
        relevanceEvidences[op] = data['options'][op]
    if 'fileString' in data:
        network = data['fileString']  # load the local network directly from user pc
        fileFormat = data["fileFormat"]
    else:
        # else load from database
        DBitem = getNetworkInDatabase(data['network'])
        network = DBitem.fileString
        fileFormat = DBitem.fileFormat

    #explanation calculation
    s = Scenario(network, fileFormat, evidences=relevanceEvidences, goals=data['goals'],
                 goalDirections=data['goalDirections'])
    nodes = s.compute_all_nodes()
    relevance = s.compute_relevancies_for_goals()
    most_relevant_nodes = list(map(lambda a: a['node_name'],
                                   filter(lambda n: n['overall_relevance'] >= 0.2 or n['node_name'] in data['options'].keys(),
                                          relevance)))
    explanation = s.compute_explanation_of_goals({}, most_relevant_nodes, nodes)
    return {'relevance': relevance, 'nodes': nodes, 'explanation': explanation}


def getNetworkInDatabase(network: str):
    """
    Queries the network name in the database and returns the corresponding entry
    :param network: network name
    :return: database entry
    """
    database_net = db.session.get(NetworkData, network)
    return database_net


def openNetwork(selectedNet: str):
    """
    Opens a network based on the network name
    :param selectedNet: the network name as in the database
    :return: opened PGMPy network
    """
    network = getNetworkInDatabase(selectedNet)
    return Network(network.fileString)


# Database object
class NetworkData(db.Model):
    fileString = db.Column(db.String(), nullable=False)
    fileFormat = db.Column(db.String(), nullable=False)
    displayName = db.Column(db.String(), primary_key=True, nullable=False)
    description = db.Column(db.String(), nullable=True)
    customization = db.Column(db.String(), nullable=True)

    def __repr__(self):
        return self.displayName


# checks if the network name passed on already exists
def doesNetworkNameExist(newDisplayName):
    if NetworkData.query.filter_by(displayName=newDisplayName).first() is not None:
        return True
    return False

"""
# Checks if the file already exists in the path
def doesPathExist(filePath):
    if os.path.exists(filePath):
        return True
    return False
"""


# Adds a new network's data to the database and saves the file to the designated path
def addNetwork(file, name, des):
    newNetwork = NetworkData(fileString=readFile(file), displayName=name, description=des)
    db.session.add(newNetwork)
    db.session.commit()
    return 'successful'


# Loads the list of known networks to the application
# returns a python dict object
@app.route('/loadNetList')
def getNetworkList():
    networks = NetworkData.query.order_by(NetworkData.displayName).all()
    netList = {}
    for i, network in enumerate(networks):
        netList[i] = network.displayName
    return netList


def readFile(file):
    """
    Function to read a .bif file and return its content as string
    :param file: The .bif file to read
    :return: str containing its content
    """
    string = file.readlines()
    string_decoded = ""
    for index in string:
        string_decoded += index.decode().replace('\r\n', '\n')
    print(string_decoded)
    return string_decoded


# Save file upload from application
@app.route('/uploadNetwork', methods=["POST"])
def saveNetwork():
    displayName = request.form['displayName']
    file = request.files['file']
    description = request.form['netDescription']
    # if the display name the user entered is already in use, return with error
    if doesNetworkNameExist(displayName):
        return jsonify('error1')
    # get file name and path
    """filename = secure_filename(file.filename)
    filePath = os.path.join(app.config['NETWORK_FOLDER'], filename)
    # if the file name of the uploaded network already exists in the networks folder, return with error
    if doesPathExist(filePath):
        return jsonify('error2')"""
    # add new network to database and save it
    addNetwork(file, displayName, description)
    return jsonify('successful')


"""
# Opens the network with requested ID and adds it to the dictionary of network objects.
# If there already exists a network object with the requested ID, the function simply returns.
@app.route('/openNetwork', methods=["POST"])
def openNetwork():
    selectedNetwork = request.get_json()
    if selectedNetwork not in NETWORKS.keys():
        network = NetworkData.query.get(selectedNetwork)
        path = network.filePath
        NETWORKS[selectedNetwork] = path
    return ''
"""
class Feedback(db.Model):
    description = db.Column(db.String(), nullable=True)
    csv = db.Column(db.String(),  nullable=True)
    date = db.Column(db.String(), nullable=True)
    ID = db.Column(db.String(), primary_key=True, nullable=False)
    mail = db.Column(db.String(), nullable=True)

    def __repr__(self):
        return self.displayName

@app.route('/sendFeedback', methods=["POST"])
def sendFeedback():
    data = request.get_json()
    newFeedback = Feedback(description=data['description'],
                             csv=data['csv'],
                             date=datetime.datetime.now(),
                             ID=str(datetime.datetime.now()) + " - " + str(random()),
                             mail=data['mail'])
    db.session.add(newFeedback)
    db.session.commit()


    return 'successful'

@app.route('/sendNetworkRequest', methods=["POST"])
def sendNetworkRequest():
    data = request.get_json()

    body = "A new network got uploaded with the request to publish it on DoctorBN."
    print(body)

    msg = MIMEMultipart()
    msg['From'] = os.environ["SENDMAIL"]
    msg['To'] = os.environ["RECEIVEMAIL"]
    msg['Subject'] = "New DoctorBN network publish request"
    msg.attach(MIMEText(body, 'plain'))
    p = MIMEBase('application', 'octet-stream')
    p.set_payload(io.StringIO(data['fileString']).read())
    encoders.encode_base64(p)
    filename = data['name'] + "." + data['fileFormat']
    p.add_header('Content-Disposition', "attachment; filename= "+filename)
    msg.attach(p)

    text = msg.as_string()

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(os.environ["SENDMAIL"], os.environ["SENDMAILPASSWORD"])
    s.sendmail(os.environ["SENDMAIL"], os.environ["RECEIVEMAIL"], text)
    s.quit()

    return 'successful'

@app.route('/')
def home():
    return 'this is the flask backend'


if __name__ == '__main__':
    app.run(host='localhost', debug=True, port=5000)
