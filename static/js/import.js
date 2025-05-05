function loc(event){
    event.preventDefault();
    alert("dsfdf")
}

/*
* Анализ текста после загрузки файла
*/
function analyze_text(event) {
        event.preventDefault();
        document.querySelector('button[name="action"][value="run_import"]').style.display = 'none';
        document.querySelector('a.btn-info').style.display = 'none';
        document.getElementById('analyzeWithAI').style.display = 'none';
        document.getElementById('fileContentPreview').style.display = 'block';
        document.getElementById("fileContentText").innerHTML = "<div class=\"spinner-border  m-5\" role=\"status\">\n" +
        "  <span class=\"sr-only\">Loading...</span>\n" +
        "</div>";

        const fileInput = event.target;
        const url = fileInput.dataset.url;
        const csrfToken = fileInput.dataset.token;

        const file = fileInput.files[0];
        if (!file) return;

        if (file.type !== "text/plain") {
            alert("Пожалуйста, загрузите текстовый файл (.txt)");
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;

            // Отправка содержимого на сервер
            fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify({ text: content })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('fileContentText').innerHTML = ""
                document.getElementById('fileContentText').innerHTML = data.result;
                window.scrollBy({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
                collectWordsData()
                document.querySelector('button[name="action"][value="run_import"]').style.display = '';
                document.querySelector('a.btn-info').style.display = '';
                document.getElementById('analyzeWithAI').style.display = '';
            })
            .catch(error => {
                console.error("Ошибка:", error);
            });
        };

        reader.readAsText(file, 'UTF-8');
}

function collectWordsData() {
        const wordsData = [];

        document.querySelectorAll('#fileContentText span[data-word]').forEach(span => {
            const word = span.getAttribute('data-word')?.trim();
            const id = span.getAttribute('data-id')?.trim() || null;
            const pos = span.getAttribute('data-pos')?.trim() || null;

            const next = span.nextSibling?.textContent?.trim();
            const match = next?.match(/\[(\d+):(\d+):(\d+):(\d+)\]/);
            const chapter = match?.[1] || null;
            const paragraph = match?.[2] || null;
            const sentence = match?.[3] || null;
            const wordindex = match?.[4] || null;

            wordsData.push({ word, id, pos, chapter, paragraph, sentence, wordindex });
        });

        const hiddenInput = document.getElementById('wordsJson');
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(wordsData);
        }
    }
