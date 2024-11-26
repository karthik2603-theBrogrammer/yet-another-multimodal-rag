const express = require('express');
const { Client, Storage, ID } = require('appwrite');
const multer = require('multer');
const fs = require('fs');
require("dotenv").config()

const app = express();
const upload = multer({ dest: 'uploads/' });

// Appwrite Configuration
const client = new Client()
    .setEndpoint('https://cloud.appwrite.io/v1')
    .setProject(process.env.APPWRITE_PROJECT_ID);

const storage = new Storage(client);


app.post('/api/insert-file', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }
        const fileBuffer = fs.readFileSync(req.file.path);
        const fileResponse = await storage.createFile(
            process.env.APPWRITE_BUCKET_ID,
            ID.unique(),
            new File([fileBuffer], req.file.originalname)
        );
        fs.unlinkSync(req.file.path);
        const downloadUrl = storage.getFileDownload(process.env.APPWRITE_BUCKET_ID, fileResponse.$id);
        res.status(200).json({
            fileId: fileResponse.$id,
            downloadUrl: downloadUrl,
            fileName: req.file.originalname
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(
        `Server running on port ${PORT}
http://localhost:${PORT}
Appwrite-Service-v1.0 is a go!`);
});