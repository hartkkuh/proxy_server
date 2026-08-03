import { uploadUrl } from "../../file_api_service.js";

const toast = document.getElementById("toast");
const uploadForm = document.getElementById("upload-form");
const urlInput = document.getElementById("url-input");
const tokenInput = document.getElementById("token-input");
const driveTokenInput = document.getElementById("drive-token-input");
const driveTokenName = document.getElementById("drive-token-name");
const uploadBtn = document.getElementById("upload-btn");
const responseSection = document.getElementById("response-section");
const responseStatus = document.getElementById("response-status");
const responseBody = document.getElementById("response-body");

if (!uploadForm || !urlInput || !tokenInput || !driveTokenInput || !uploadBtn) {
    throw new Error("שגיאה בטעינת הדף. נסה לרענן עם Ctrl+Shift+R");
}

let toastTimer;

function showToast(message, type = "success") {
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.className = `toast visible ${type}`;
    toastTimer = setTimeout(() => {
        toast.classList.remove("visible");
    }, 4000);
}

function extractError(data) {
    if (typeof data === "string") return data;
    if (data?.error) return data.error;
    if (data?.message) return data.message;
    return "שגיאה לא ידועה";
}

function getNetworkErrorMessage(err) {
    if (err instanceof TypeError && err.message === "Failed to fetch") {
        return "שגיאת רשת: לא ניתן להפעיל את הטריגר. בדוק CORS, GITHUB_TOKEN והרשאות ל-repo.";
    }
    return err.message;
}

function formatResponseBody(data, status) {
    return JSON.stringify({ status, ...data }, null, 2);
}

function showResponse(data, status) {
    const isSuccess = data.success === true;

    responseSection.classList.remove("hidden", "success", "error");
    responseSection.classList.add(isSuccess ? "success" : "error");

    responseStatus.textContent = isSuccess ? "הצלחה" : "שגיאה";
    responseBody.textContent = formatResponseBody(data, status);
}

function parseUrls(text) {
    return text
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
}

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsText(file);
    });
}

driveTokenInput.addEventListener("change", () => {
    const file = driveTokenInput.files?.[0];
    if (driveTokenName) {
        driveTokenName.textContent = file ? `נבחר: ${file.name}` : "";
    }
});

uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const urls = parseUrls(urlInput.value);
    const githubToken = tokenInput.value.trim();
    const driveTokenFile = driveTokenInput.files?.[0];

    if (!urls.length || !githubToken || !driveTokenFile) return;

    let driveToken;
    try {
        driveToken = JSON.parse(await readFileAsText(driveTokenFile));
    } catch {
        showToast("קובץ token.json לא תקין", "error");
        return;
    }

    uploadBtn.disabled = true;
    uploadBtn.textContent = "שולח...";

    try {
        const results = [];

        for (const url of urls) {
            const { data, status } = await uploadUrl(url, driveToken, githubToken);
            results.push({ url, status, ...data });
        }

        const allSuccess = results.every((item) => item.success === true);
        showResponse(
            {
                success: allSuccess,
                message: allSuccess
                    ? "כל הטריגרים הופעלו, ההורדה והעלאה לדרייב מתבצעות ב-GitHub Actions"
                    : "חלק מהטריגרים נכשלו",
                results,
            },
            allSuccess ? 204 : 400
        );

        if (allSuccess) {
            showToast("הבקשות נשלחו בהצלחה", "success");
            urlInput.value = "";
            driveTokenInput.value = "";
            if (driveTokenName) driveTokenName.textContent = "";
        } else {
            showToast("חלק מהבקשות נכשלו", "error");
        }
    } catch (err) {
        const message = getNetworkErrorMessage(err);

        if (responseSection && responseStatus && responseBody) {
            responseSection.classList.remove("hidden", "success");
            responseSection.classList.add("error");
            responseStatus.textContent = "שגיאה";
            responseBody.textContent = formatResponseBody({ error: message }, "—");
        }

        showToast(message, "error");
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = "העלה לדרייב";
    }
});
