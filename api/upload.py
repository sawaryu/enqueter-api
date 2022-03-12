import base64
import datetime
import http
import os
import tempfile
import traceback

import boto3
from io import BytesIO

from PIL import Image
from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource

from database import db

upload_ns = Namespace('/upload', description="masked(can`t open)")

client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "sample"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "sample"),
    region_name=os.getenv("AWS_REGION", "sample"),
)


@upload_ns.route('')
class UploadUserAvatar(Resource):
    @upload_ns.hide
    @upload_ns.doc(
        security='jwt_auth',
        description='Upload avatar to S3.'
    )
    @jwt_required()
    def post(self):
        if not request.method == 'POST':
            return {"message": "invalid request"}, http.HTTPStatus.BAD_REQUEST

        try:
            with tempfile.NamedTemporaryFile() as temp_image_file:

                # only string binary data
                base64_png = request.form['image']
                if type(base64_png) is not str:
                    return {"message": "invalid request"}, http.HTTPStatus.BAD_REQUEST

                # decode
                code = base64.b64decode(base64_png.split(',')[1])

                # if valid image format, "UnidentifiedImageError" occur
                image = Image.open(BytesIO(code))

                # sizing
                image = scale_to_width(image=image, width=170)

                # if image is broken, error occur
                image.verify()

                # save in temp_file
                image.save(temp_image_file, "PNG")

                # seek
                temp_image_file.seek(0)

                now = datetime.datetime.now()
                filename = now.strftime('%Y%m%d_%H%M%S_%f') + str(current_user.id) + ".png"
                stream = temp_image_file

                # upload
                client.upload_fileobj(
                    Fileobj=stream,
                    Bucket=os.getenv("AWS_BUCKET_NAME"),
                    Key=f'{os.getenv("AWS_PATH_KEY")}{filename}',
                    ExtraArgs={"ACL": "public-read", "ContentType": "image/png"}
                )

                # delete if avatar name not! include "egg"
                if "egg" not in current_user.avatar:
                    client.delete_object(
                        Bucket=os.getenv("AWS_BUCKET_NAME"),
                        Key=f'{os.getenv("AWS_PATH_KEY")}{current_user.avatar}'
                    )

                # save
                current_user.avatar = filename
                db.session.commit()

            return {"message": "success"}, 201
        except:
            traceback.print_exc()
            return {"message": "Internal server error. Failed to upload the avatar."}, 500


# Sustain aspect ratio.
def scale_to_width(image, width):
    height = round(image.height * width / image.width)
    return image.resize((width, height))
