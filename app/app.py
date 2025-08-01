from flask import Flask, render_template, request, send_from_directory
from pymysql import connections
import os
import random
import argparse
import boto3
import logging
from botocore.exceptions import ClientError

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DBHOST = os.environ.get("DBHOST") or "localhost"
DBUSER = os.environ.get("DBUSER") or "root"
DBPWD = os.environ.get("DBPWD") or "password"
DATABASE = os.environ.get("DATABASE") or "employees"
COLOR_FROM_ENV = os.environ.get('APP_COLOR') or "lime"
DBPORT = int(os.environ.get("DBPORT", 3306))
YOUR_NAME = os.environ.get("YOUR_NAME") or "CLO835 Student"

# S3 Configuration for background image download
S3_BUCKET = os.environ.get("S3_BUCKET") or "clo835-finalproject-g8"
S3_IMAGE_KEY = os.environ.get("S3_IMAGE_KEY") or "background.jpg"
AWS_REGION = os.environ.get("AWS_REGION") or "us-east-1"
LOCAL_IMAGES_FOLDER = "images"  # Local folder for downloaded images

# Create a connection to the MySQL database
db_conn = connections.Connection(
    host=DBHOST,
    port=DBPORT,
    user=DBUSER,
    password=DBPWD, 
    db=DATABASE
)

# Define the supported color codes
color_codes = {
    "red": "#e74c3c",
    "green": "#16a085",
    "blue": "#89CFF0",
    "blue2": "#30336b",
    "pink": "#f4c2c2",
    "darkblue": "#130f40",
    "lime": "#C1FF9C",
}

SUPPORTED_COLORS = ",".join(color_codes.keys())
COLOR = random.choice(["red", "green", "blue", "blue2", "darkblue", "pink", "lime"])

def download_background_image():
    """Download background image from S3 and store locally"""
    try:
        # Create S3 client
        s3 = boto3.client('s3', region_name=AWS_REGION)
        
        # Create local images folder if it doesn't exist
        if not os.path.exists(LOCAL_IMAGES_FOLDER):
            os.makedirs(LOCAL_IMAGES_FOLDER)
            logger.info(f"Created folder: {LOCAL_IMAGES_FOLDER}")
        
        # Get filename from S3 key
        filename = os.path.basename(S3_IMAGE_KEY)
        local_path = os.path.join(LOCAL_IMAGES_FOLDER, filename)
        
        # Check if image already exists locally
        if os.path.exists(local_path):
            logger.info(f"Background image already exists locally: {local_path}")
            return f"/static/images/{filename}"
        
        # Download the image
        logger.info(f"Downloading {S3_IMAGE_KEY} from bucket {S3_BUCKET}...")
        s3.download_file(S3_BUCKET, S3_IMAGE_KEY, local_path)
        
        logger.info(f"✅ Background image downloaded successfully!")
        logger.info(f"📁 Saved to: {local_path}")
        
        # Return the URL path for the template
        return f"/images/{filename}"
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"S3 bucket '{S3_BUCKET}' does not exist")
        elif error_code == 'NoSuchKey':
            logger.error(f"S3 object '{S3_IMAGE_KEY}' not found in bucket '{S3_BUCKET}'")
        elif error_code == 'AccessDenied':
            logger.error("Access denied to S3. Check your AWS credentials and permissions")
        else:
            logger.error(f"S3 ClientError: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error downloading background image: {e}")
        return None

def get_background_image():
    """Get the background image URL (local path after download)"""
    # First try to download/get local image
    local_image_url = download_background_image()
    
    if local_image_url:
        logger.info(f"Using local background image: {local_image_url}")
        return local_image_url
    else:
        # Fallback to direct S3 URL if download fails
        fallback_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{S3_IMAGE_KEY}"
        logger.info(f"Fallback to S3 URL: {fallback_url}")
        return fallback_url

@app.route("/", methods=['GET', 'POST'])
def home():
    background_image = get_background_image()
    return render_template('addemp.html', color=color_codes[COLOR], 
                         background_image=background_image, user_name=YOUR_NAME)

@app.route("/about", methods=['GET','POST'])
def about():
    background_image = get_background_image()
    return render_template('about.html', color=color_codes[COLOR], 
                         background_image=background_image, user_name=YOUR_NAME)
    
@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        cursor.execute(insert_sql,(emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
    finally:
        cursor.close()

    print("all modification done...")
    background_image = get_background_image()
    return render_template('addempoutput.html', name=emp_name, 
                         color=color_codes[COLOR], background_image=background_image)

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    background_image = get_background_image()
    return render_template("getemp.html", color=color_codes[COLOR], 
                         background_image=background_image)

@app.route("/fetchdata", methods=['GET','POST'])
def FetchData():
    emp_id = request.form['emp_id']
    output = {}
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location from employee where emp_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql,(emp_id))
        result = cursor.fetchone()
        
        output["emp_id"] = result[0]
        output["first_name"] = result[1]
        output["last_name"] = result[2]
        output["primary_skills"] = result[3]
        output["location"] = result[4]
        
    except Exception as e:
        print(e)
    finally:
        cursor.close()

    background_image = get_background_image()
    return render_template("getempoutput.html", id=output["emp_id"], fname=output["first_name"],
                           lname=output["last_name"], interest=output["primary_skills"], 
                           location=output["location"], color=color_codes[COLOR],
                           background_image=background_image)

# Route to serve images from the images folder
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(LOCAL_IMAGES_FOLDER, filename)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--color', required=False)
    args = parser.parse_args()

    if args.color:
        print("Color from command line argument =" + args.color)
        COLOR = args.color
        if COLOR_FROM_ENV:
            print("A color was set through environment variable -" + COLOR_FROM_ENV + ". However, color from command line argument takes precendence.")
    elif COLOR_FROM_ENV:
        print("No Command line argument. Color from environment variable =" + COLOR_FROM_ENV)
        COLOR = COLOR_FROM_ENV
    else:
        print("No command line argument or environment variable. Picking a Random Color =" + COLOR)

    if COLOR not in color_codes:
        print("Color not supported. Received '" + COLOR + "' expected one of " + SUPPORTED_COLORS)
        exit(1)

    # Download background image on startup
    logger.info("Initializing background image download...")
    background_image_url = get_background_image()
    logger.info(f"Background image ready: {background_image_url}")
    
    app.run(host='0.0.0.0',port=81,debug=True)