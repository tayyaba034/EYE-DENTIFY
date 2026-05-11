const { S3Client, PutObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');
const { v4: uuidv4 } = require('uuid');

const s3Client = new S3Client({
    region: process.env.AWS_REGION,
    credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    },
});

/**
 * Generate a signed URL for uploading to S3
 * @param {string} contentType e.g. 'image/jpeg'
 * @returns {Object} { uploadUrl, key }
 */
async function getUploadSignedUrl(contentType) {
    const key = `${uuidv4()}`;
    const command = new PutObjectCommand({
        Bucket: process.env.AWS_S3_BUCKET,
        Key: key,
        ContentType: contentType,
    });

    const uploadUrl = await getSignedUrl(s3Client, command, { expiresIn: 60 });
    return { uploadUrl, key };
}

/**
 * Generate a signed URL for reading from S3
 * @param {string} key 
 * @returns {string} signedUrl
 */
async function getReadSignedUrl(key) {
    if (!key) return null;
    const command = new GetObjectCommand({
        Bucket: process.env.AWS_S3_BUCKET,
        Key: key,
    });

    return await getSignedUrl(s3Client, command, { expiresIn: 3600 }); // 1 hour
}

module.exports = { getUploadSignedUrl, getReadSignedUrl };
