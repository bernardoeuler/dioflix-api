const API_BASE = "http://localhost:7071/api";

async function fetchMovies() {
  try {
    const res = await fetch(`${API_BASE}/movies`);
    const movies = await res.json();
    const grid = document.getElementById("movies-grid");
    grid.innerHTML = movies.map(movie => `
      <div class="movie-card" onclick="location.href='movie.html?id=${movie.id}'">
        <img src="${movie.thumb}" alt="${movie.title}">
        <div class="info">
          <h3>${movie.title}</h3>
          <p>${movie.year}</p>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

async function fetchMovieDetail() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  try {
    const res = await fetch(`${API_BASE}/movies/${id}`);
    const movie = await res.json();
    const detailDiv = document.getElementById("movie-detail");
    detailDiv.innerHTML = `
      <h2>${movie.title}</h2>
      <video src="${movie.video}" controls width="800"></video>
      <p>Ano: ${movie.year}</p>
    `;
  } catch (err) {
    console.error(err);
  }
}

const uploadForm = document.getElementById("upload-form");
if (uploadForm) {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("title").value;
    const year = document.getElementById("year").value;
    const thumb = document.getElementById("thumb").files[0];
    const video = document.getElementById("video").files[0];
    const message = document.getElementById("message");

    try {
      // Upload thumbnail
      const thumbForm = new FormData();
      thumbForm.append("file", thumb);
      const thumbRes = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: thumbForm,
        headers: { "file-type": "image" }
      });
      const thumbData = await thumbRes.json();

      // Upload video
      const videoForm = new FormData();
      videoForm.append("file", video);
      const videoRes = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: videoForm,
        headers: { "file-type": "video" }
      });
      const videoData = await videoRes.json();

      // Add movie
      const movieRes = await fetch(`${API_BASE}/movies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          year: parseInt(year),
          thumb: thumbData.blobUri,
          video: videoData.blobUri
        })
      });
      await movieRes.json();
      message.textContent = "Filme enviado com sucesso!";
      uploadForm.reset();
    } catch (err) {
      console.error(err);
      message.textContent = "Erro ao enviar filme.";
    }
  });
}
