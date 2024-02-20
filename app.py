from urllib.parse import quote_plus
from flask import Flask, jsonify, request
from sqlalchemy import create_engine, inspect, Column, Integer, String, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from flask_cors import CORS
from sqlalchemy.orm import sessionmaker
import spacy
import random
from fuzzywuzzy import process, fuzz
nlp = spacy.load("en_core_web_sm")

app = Flask(__name__)
CORS(app)

Base = declarative_base()


app = Flask(__name__)
CORS(app)

Base = declarative_base()


app.config['SQLALCHEMY_DATABASE_USER'] = 'chikku_chatbot_data_user'
app.config['SQLALCHEMY_DATABASE_PASSWORD'] = 'x07zIKvY9Zan4lRB3iSntvQgQD9fjVi6'
app.config['SQLALCHEMY_DATABASE_HOST'] = 'dpg-cmqv2u21hbls73fm81tg-a.oregon-postgres.render.com'
app.config['SQLALCHEMY_DATABASE_PORT'] = '5432'  # Assuming the default PostgreSQL port is used
app.config['SQLALCHEMY_DATABASE_NAME'] = 'chikku_chatbot_data'

# Construct the new URI
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{app.config['SQLALCHEMY_DATABASE_USER']}:{quote_plus(app.config['SQLALCHEMY_DATABASE_PASSWORD'])}@{app.config['SQLALCHEMY_DATABASE_HOST']}:{app.config['SQLALCHEMY_DATABASE_PORT']}/{app.config['SQLALCHEMY_DATABASE_NAME']}"



# Replace the connection string with your actual PostgreSQL connection string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


class Intent(Base):
    __tablename__ = 'chatbot_data'
    # __table_args__ = {'schema': 'chikkuchatbot'}
    id = Column(Integer, primary_key=True)
    tag = Column(String(50), unique=True, nullable=False)
    patterns = Column(ARRAY(String), nullable=False)
    responses = Column(ARRAY(String), nullable=False)

# Create the 'chikkuchatbot' schema if it doesn't exist
with app.app_context():
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    Base.metadata.create_all(bind=engine)

# API endpoint for adding new intents
@app.route('/api/intents', methods=['POST'])
def add_intent():
    # Extract data from the request
    data = request.get_json()

    tag = data.get('tag')
    patterns = data.get('patterns')
    responses = data.get('responses')

    # Validate data
    if not tag or not patterns or not responses:
        return jsonify({'error': 'Incomplete data provided'}), 400

    # Create a new intent
    new_intent = Intent(tag=tag, patterns=patterns, responses=responses)

    # Add the new intent to the database
    with app.app_context():
        Session = sessionmaker(bind=engine)
        session = Session()

        session.add(new_intent)
        session.commit()

    return jsonify({'message': 'Intent added successfully'})


@app.route('/api/fetch', methods=['GET'])
def get_intents():
    # Create a session within the application context
    with app.app_context():
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check if the 'Intent' table exists in the database
        inspector = inspect(engine)
        table_exists = inspector.has_table("chatbot_data") #, schema="chikkuchatbot")

        # Query data from the "chatbot_data" table if it exists
        if table_exists:
            intents = session.query(Intent).all()
            intent_list = []
            for intent in intents:
                intent_list.append({
                    'id': intent.id,
                    'tag': intent.tag,
                    'patterns': intent.patterns,
                    'responses': intent.responses
                })
        else:
            intent_list = []

    return jsonify({'intents': intent_list})

@app.route('/api/data/<int:intent_id>', methods=['DELETE'])
def delete_intent(intent_id):
    # Create a session within the application context
    with app.app_context():
        Session = sessionmaker(bind=engine)
        session = Session()

        # Retrieve the intent by ID
        intent = session.query(Intent).filter_by(id=intent_id).first()

        # Check if the intent exists
        if not intent:
            return jsonify({'error': 'Intent not found'}), 404

        # Delete the intent
        session.delete(intent)
        session.commit()

    return jsonify({'message': f'Intent with ID {intent_id} deleted successfully'})


@app.route('/api/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')

    if not question:
        return jsonify({'error': 'Missing question'}), 400

    # Use spaCy to process the question
    doc = nlp(question.lower())

    # Find the most relevant intent based on spaCy processing
    relevant_intent = None
    max_score = 0

    # Use the scoped session to query the database
    Session = sessionmaker(bind=engine)
    session = Session()
    intents = session.query(Intent).all()

    for intent in intents:
        # Use fuzzy matching to find the similarity score
        _, score = process.extractOne(question.lower(), intent.patterns, scorer=fuzz.ratio)

        # Update relevant_intent if a better match is found
        if score > max_score:
            max_score = score
            relevant_intent = intent

    # Respond based on the relevant intent
    if relevant_intent and max_score >= 70:  # Adjust the threshold as needed
        response =relevant_intent.responses
    else:
        response = "I'm sorry, I don't understand the question."

    return jsonify({'response': response})



if __name__ == '__main__':
    app.run(debug=True)