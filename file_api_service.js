const GITHUB_OWNER = "hartkhartk";
const GITHUB_REPO = "server";
const DISPATCH_EVENT = "proxy_request";
const YOUTUBE_DISPATCH_EVENT = "youtube_request";
const GET_LIST_DISPATCH_EVENT = "get_list";
const GOOGLE_SEARCH_DISPATCH_EVENT = "google_search";
const DUCKDUCKGO_SEARCH_DISPATCH_EVENT = "duckduckgo_search";
const GROQ_CHAT_DISPATCH_EVENT = "groq_chat";
const DOWNLOAD_YOUTUBE_DISPATCH_EVENT = "download_youtube";
const DOWNLOAD_WEBSITE_DISPATCH_EVENT = "download_website";

async function dispatchUrl(url, token, eventType) {
    if (!token) {
        return {
            data: {
                success: false,
                error: "חסר GitHub Token",
            },
            ok: false,
            status: 0,
        };
    }
    const clientPayload =
        eventType === YOUTUBE_DISPATCH_EVENT
            ? { videos: url, token }
            : eventType === GET_LIST_DISPATCH_EVENT
              ? { url, token }
              : { url };

    const response = await fetch(
        `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/dispatches`,
        {
            method: "POST",
            headers: {
                Accept: "application/vnd.github+json",
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            body: JSON.stringify({
                event_type: eventType,
                client_payload: clientPayload,
            }),
        }
    );

    if (response.status === 204) {
        const data = {
            success: true,
            message: "הטריגר הופעל, הבקשה נשלחת לשרת דרך GitHub Actions",
        };
        if (eventType === YOUTUBE_DISPATCH_EVENT) {
            data.videos = url;
            data.token = token;
        } else if (eventType === GET_LIST_DISPATCH_EVENT) {
            data.url = url;
            data.token = token;
        } else {
            data.url = url;
        }
        return {
            data,
            ok: true,
            status: response.status,
        };
    }

    let errorData = {};
    try {
        errorData = await response.json();
    } catch {
        errorData = {};
    }

    return {
        data: {
            success: false,
            error: getDispatchErrorMessage(response.status, errorData.message),
            url,
        },
        ok: false,
        status: response.status,
    };
}

export const uploadYoutube = (videos, token) => dispatchUrl(videos, token, YOUTUBE_DISPATCH_EVENT);
export const getList = (url, token) => dispatchUrl(url, token, GET_LIST_DISPATCH_EVENT);
export const getYoutubeList = (url, token) => dispatchUrl(url, token, GET_LIST_DISPATCH_EVENT);

function getDispatchErrorMessage(status, message) {
    if (status === 403 && message === "Resource not accessible by personal access token") {
        return "ל-token חסרה הרשאת Contents (Read and write) ל-repo server. הרשאת Actions בלבד לא מספיקה.";
    }

    return message || "שגיאה בהפעלת הטריגר";
}

async function dispatchPayload(clientPayload, token, eventType) {
    if (!token) {
        return {
            data: { success: false, error: "חסר GitHub Token" },
            ok: false,
            status: 0,
        };
    }

    const response = await fetch(
        `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/dispatches`,
        {
            method: "POST",
            headers: {
                Accept: "application/vnd.github+json",
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            body: JSON.stringify({
                event_type: eventType,
                client_payload: clientPayload,
            }),
        }
    );

    if (response.status === 204) {
        return {
            data: {
                success: true,
                message:
                    eventType === DOWNLOAD_YOUTUBE_DISPATCH_EVENT ||
                    eventType === DISPATCH_EVENT
                        ? "הטריגר הופעל, ההורדה והעלאה לדרייב מתבצעות ב-GitHub Actions"
                        : eventType === DOWNLOAD_WEBSITE_DISPATCH_EVENT
                          ? "הטריגר הופעל, הורדת האתר והעלאה לדרייב מתבצעות ב-GitHub Actions"
                          : eventType === DUCKDUCKGO_SEARCH_DISPATCH_EVENT
                            ? "הטריגר הופעל, החיפוש נשמר כ-HTML ב-artifact של GitHub Actions"
                            : "הטריגר הופעל, הבקשה נשלחת לשרת דרך GitHub Actions",
                ...clientPayload,
            },
            ok: true,
            status: response.status,
        };
    }

    let errorData = {};
    try {
        errorData = await response.json();
    } catch {
        errorData = {};
    }

    return {
        data: {
            success: false,
            error: getDispatchErrorMessage(response.status, errorData.message),
            ...clientPayload,
        },
        ok: false,
        status: response.status,
    };
}

export async function googleSearch({ text, site, tag }, token) {
    if (!text?.trim()) {
        return {
            data: { success: false, error: "חסר טקסט חיפוש" },
            ok: false,
            status: 0,
        };
    }

    const clientPayload = { text: text.trim() };
    const siteValue = site?.trim();
    const tagValue = tag?.trim();
    if (siteValue) clientPayload.site = siteValue;
    if (tagValue) clientPayload.tag = tagValue;

    return dispatchPayload(clientPayload, token, GOOGLE_SEARCH_DISPATCH_EVENT);
}

const DUCKDUCKGO_SEARCH_TYPES = new Set(["web", "images", "videos", "news"]);

export async function duckduckgoSearch({ question, type }, token) {
    if (!question?.trim()) {
        return {
            data: { success: false, error: "חסרה שאלה" },
            ok: false,
            status: 0,
        };
    }

    const typeValue = type?.trim();
    if (!typeValue) {
        return {
            data: { success: false, error: "חסר סוג" },
            ok: false,
            status: 0,
        };
    }
    if (!DUCKDUCKGO_SEARCH_TYPES.has(typeValue)) {
        return {
            data: {
                success: false,
                error: "סוג חיפוש לא תקין. בחר: web, images, videos או news",
            },
            ok: false,
            status: 0,
        };
    }

    return dispatchPayload(
        { question: question.trim(), type: typeValue },
        token,
        DUCKDUCKGO_SEARCH_DISPATCH_EVENT
    );
}

export async function groqChat({ prompt, zip, filename }, token) {
    if (!prompt?.trim()) {
        return {
            data: { success: false, error: "חסר פרומפט" },
            ok: false,
            status: 0,
        };
    }

    const clientPayload = { prompt: prompt.trim() };
    if (zip) {
        clientPayload.zip = true;
        if (filename) clientPayload.filename = filename;
    }

    return dispatchPayload(clientPayload, token, GROQ_CHAT_DISPATCH_EVENT);
}

export async function uploadUrl(url, driveToken, githubToken) {
    if (!url?.trim()) {
        return {
            data: { success: false, error: "חסר URL" },
            ok: false,
            status: 0,
        };
    }
    if (!driveToken || typeof driveToken !== "object") {
        return {
            data: { success: false, error: "חסר token.json תקין ל-Google Drive" },
            ok: false,
            status: 0,
        };
    }

    const result = await dispatchPayload(
        { url: url.trim(), token: driveToken },
        githubToken,
        DISPATCH_EVENT
    );

    if (result.data?.token) {
        delete result.data.token;
    }

    return result;
}

export async function downloadYoutube(url, driveToken, githubToken) {
    if (!url?.trim()) {
        return {
            data: { success: false, error: "חסר URL" },
            ok: false,
            status: 0,
        };
    }
    if (!driveToken || typeof driveToken !== "object") {
        return {
            data: { success: false, error: "חסר token.json תקין ל-Google Drive" },
            ok: false,
            status: 0,
        };
    }

    const result = await dispatchPayload(
        { url: url.trim(), token: driveToken },
        githubToken,
        DOWNLOAD_YOUTUBE_DISPATCH_EVENT
    );

    if (result.data?.token) {
        delete result.data.token;
    }

    return result;
}

export async function downloadWebsite(url, driveToken, githubToken) {
    if (!url?.trim()) {
        return {
            data: { success: false, error: "חסר URL" },
            ok: false,
            status: 0,
        };
    }
    if (!driveToken || typeof driveToken !== "object") {
        return {
            data: { success: false, error: "חסר token.json תקין ל-Google Drive" },
            ok: false,
            status: 0,
        };
    }

    const result = await dispatchPayload(
        { url: url.trim(), token: driveToken },
        githubToken,
        DOWNLOAD_WEBSITE_DISPATCH_EVENT
    );

    if (result.data?.token) {
        delete result.data.token;
    }

    return result;
}
