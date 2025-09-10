// For local testing (Flask default): 
const API_URL = "http://127.0.0.1:5000/summarize";

// When you deploy to Render, change it to:
// const API_URL = "https://your-backend.onrender.com/summarize";



document.getElementById("btnSearch").addEventListener("click", async () => {
    const url = document.getElementById("url").value;
    const output = document.getElementById("sum");

    output.textContent = "Loading...";

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }) // send JSON {url: "..."}
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        // Assuming API returns { "summary": "..." }
        output.textContent = data.summary || "No summary returned.";
    } catch (err) {
        output.textContent = "❌ Error: " + err.message;
    }
});

/////////////////////


// script.js

// document.getElementById("btnSearch").addEventListener("click", async () => {
//     const url = document.getElementById("url").value;
//     const sumLabel = document.getElementById("sum");

//     sumLabel.textContent = "Loading..."; // Show feedback while waiting

//     try {
//         const response = await fetch("http://127.0.0.1:5000/summarize", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json"
//             },
//             body: JSON.stringify({ url: url })
//         });

//         if (!response.ok) {
//             throw new Error(`HTTP error! status: ${response.status}`);
//         }

//         const data = await response.json();
//         sumLabel.textContent = data.summary; // adjust key if your API returns differently
//     } catch (error) {
//         console.error("Error fetching summary:", error);
//         sumLabel.textContent = "Error fetching summary. Check console.";
//     }
// });
