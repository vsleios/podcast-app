import os
from dotenv import load_dotenv

load_dotenv("/home/bill/Documents/podcast-app/secrets.env")

api_key = os.getenv("API_KEY")

import re
import numpy as np
from google import genai
from google.genai import types

import umap
import hdbscan

from youtube_transcript_api import YouTubeTranscriptApi



def good_entry(text):
    text = text.strip(" -.,!@#$%^&*()_<>?:'/[]{}")
    if text[0] != text[0].lower():
        return True
    else:
        return False

def get_duration(l, metascript):
    return( metascript[l[-1]]["start"] + metascript[l[-1]]["duration"] - metascript[l[0]]["start"] )

def reassign_noise_runs(cluster_labels, min_run_length=3):
    cluster_labels = cluster_labels.copy()
    current_label = max(cluster_labels)+1
    i = 0
    while i < len(cluster_labels):
        if cluster_labels[i] == -1:
            start = i
            while i < len(cluster_labels) and cluster_labels[i] == -1:
                i += 1
            run_length = i - start
            if run_length >= min_run_length:
                cluster_labels[start:i] = current_label
                current_label += 1
        else:
            i += 1
    return cluster_labels


system_prompt = f"""
You are writing content that will be shown directly to podcast listeners on a website.

You will be given a podcast transcript that has been segmented into labeled sections. Each section starts with a marker in the form `=== SECTION X ===` (where X is a number). You must strictly follow this structure and keep your output aligned to the provided sections — do not create new sections or merge existing ones.

Your tasks are:

1. Write a short, engaging paragraph (2–3 sentences) summarizing the podcast as a whole. This goes at the top.

2. For each section:
   - Keep the section marker exactly as it appears (e.g., `=== SECTION 2 ===`)
   - **On the next line**, write a **bolded title** summarizing that section.
   - Then on the following lines, write **2 to 5 short bullet points** summarizing the most important or interesting content. Bullet points should be concise and easy to scan.

✅ Your output must follow this exact formatting:

- The section marker on its own line  
- The title on its own line, in bold  
- Then the bullet points  
- Use clean line breaks between elements

🚫 Do not hallucinate or invent new sections. Only use the sections as provided. Do not move or merge sections.

❗Do not include phrases like "Title:", "Bullet Points:", or "Summary:". Just clean content.

---

Example:

=== SECTION 0 ===  
**The Rise of AI in Everyday Life**  
- AI is becoming more integrated into daily routines through tools like smart assistants  
- Experts discuss the ethical implications of AI in decision-making  
- Self-driving technology is used as a case study of real-world AI adoption  
- Panelists share differing views on the risks and benefits of AI proliferation  

---

"""




def generate_summary(url: str) -> dict:
    
    video_id = url[32:]

    metascript = YouTubeTranscriptApi().fetch(video_id).to_raw_data()

    i=0
    chunks_list = []

    while i < len(metascript):
        chunk = []; s=0; flag=True
        while flag and i<len(metascript):
            chunk.append(i)
            s = get_duration(chunk, metascript)
            i += 1
            if s>110 and s<120:
                if good_entry(metascript[i]["text"]) == True:
                    flag = False
            if s>120:
                flag=False
                i -= 1
                chunk.remove(chunk[-1])
        chunks_list.append(chunk)

    
    chunks_txt = []
    for l in chunks_list:
        s = ""
        for e in l:
            s += re.sub(r'(?<!\n)\n(?!\n)', ' ', metascript[e]["text"])
            s += " "
            # s += metascript[e]["text"]
        chunks_txt.append(s)

    client = genai.Client(api_key=api_key)

    quo = len(chunks_txt)//100; res = len(chunks_txt) % 100

    chunks_emb = []

    for i in range(quo):
        result = client.models.embed_content(
                model="models/text-embedding-004",
                contents= chunks_txt[i*100:i*100+100],
                config=types.EmbedContentConfig(task_type="CLUSTERING")
        )

        batch = [np.array(e.values) for e in result.embeddings]

        chunks_emb = chunks_emb + batch
        

    result = client.models.embed_content(
            model="models/text-embedding-004",
            contents= chunks_txt[quo*100:quo*100+res+1],
            config=types.EmbedContentConfig(task_type="CLUSTERING")
    )

    batch = [np.array(e.values) for e in result.embeddings]

    chunks_emb = chunks_emb + batch


    emb = np.array(chunks_emb)


    umap_model = umap.UMAP(n_neighbors=15, n_components=10, metric='cosine', random_state=42)
    emb_umap = umap_model.fit_transform(emb)  # Resulting shape: (n_chunks, 10)

    # Step 2: HDBSCAN clustering
    clusterer = hdbscan.HDBSCAN(min_cluster_size=6,  # Adjust based on your expected section length
                                min_samples=1,
                                metric='euclidean',  # Use 'euclidean' after UMAP
                                cluster_selection_method='eom',
                                prediction_data=True)

    cluster_labels = clusterer.fit_predict(emb_umap)  # -1 means noise/unassigned

    
    clusters = reassign_noise_runs(cluster_labels, min_run_length=3)

    labels = []
    for e in clusters:
        if e != -1 and e not in labels:
            labels.append(e)
    print(labels)

    sections = "\n\n"

    for i in range(len(labels)):
        
        sections += f"=== SECTION {i} ===\n\n"
        
        s=""
        for j in range(len(clusters)):
            if clusters[j] == labels[i]:
                s += (chunks_txt[j]+"\n\n")
                
        sections += s


    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt),
        contents=f"Summarize the following podcast: {sections}"
    )


    res = re.sub(r"^=== SECTION \d+ ===\s*", "", response.text, flags=re.MULTILINE)



    return res

