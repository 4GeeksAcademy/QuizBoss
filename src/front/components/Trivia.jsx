import { useState } from "react";

export default function Trivia() {
  const [trivia, setTrivia] = useState(null);
  const [loading, setLoading] = useState(false);

  async function generarTrivia() {
    setLoading(true);
    setTrivia(null);
    
    const response = await fetch("https://api.perplexity.ai/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${import.meta.env.VITE_PERPLEXITY_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "sonar",
        messages: [
          { role: "system", content: "Eres un generador de trivias." },
          { role: "user", content: crearPrompt('ciencia', 'facil') }
        ],
        temperature: 0.7,
        max_tokens: 300
      })
    });

    const data = await response.json();
    const content = data.choices[0].message.content;
    const start = content.indexOf("{");
    const end = content.lastIndexOf("}");
    const triviaJson = content.slice(start, end + 1);
    const triviaObj = JSON.parse(triviaJson);

    setTrivia(triviaObj);
    setLoading(false);
  }

  return (
    <div>
      <h1>Generador de Trivia</h1>
      <button onClick={generarTrivia} disabled={loading}>
        {loading ? "Cargando..." : "Generar Pregunta de Trivia"}
      </button>
      {trivia && (
        <div className="mt-4">
          <h3>{trivia.question}</h3>
          <ul>
            {trivia.options.map((option, idx) => (
              <li key={idx}>
                {option}
                {option === trivia.correct_answer && (
                  <span style={{ color: "green", marginLeft: 8 }}>(Correcta)</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function crearPrompt(categoria, dificultad) {
  return `
Crea una pregunta de trivia de dificultad ${dificultad.toUpperCase()} sobre el tema ${categoria.toUpperCase()}.
Debe tener 4 opciones de respuesta y marcar cuál es la correcta. Devuélvelo en formato JSON como este ejemplo:

{
  "question": "¿Qué partícula subatómica tiene carga negativa?",
  "options": ["Protón", "Neutrón", "Electrón", "Fotón"],
  "correct_answer": "Electrón"
}
  `;
}



