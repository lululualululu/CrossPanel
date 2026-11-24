const byId = (id) => document.getElementById(id);
const sources = {
  'CP-002421': ['Sun et al. · Fig. 2', '10.1038/s41467-023-41708-6', 'Shape-morphing module, photographs and control signals'],
  'CP-002425': ['Zhang et al. · Fig. 2', '10.1038/s41467-023-38648-6', 'Fluid patterns at different flow rates in experiments and simulations'],
  'CP-000150': ['Johnston & Fusi · Fig. 4', '10.1038/s41467-023-36583-0', 'Generalization in neural networks trained on grid and mixed tasks'],
  'CP-000153': ['Balasubramanian et al. · Fig. 3', '10.1038/s41467-023-40114-2', 'Synchronization errors and latencies of three wearable devices'],
};

async function loadSamples() {
  const responses = await Promise.all(['questions.jsonl', 'answers.json'].map(path => fetch('samples/' + path)));
  if (responses.some(r => !r.ok)) throw new Error('Sample files unavailable');
  const questions = (await responses[0].text()).trim().split('\n').map(line => JSON.parse(line));
  const answers = await responses[1].json();
  const picker = byId('sample-pick');
  function display() {
    const q = questions.find(item => item.id === picker.value);
    const [credit, doi, alt] = sources[q.id];
    const lines = q.prompt.split('\n');
    const stem = lines.findIndex(line => line.startsWith('Question: '));
    const options = lines.findIndex(line => line.startsWith('A. '));
    byId('question').textContent = lines[stem].slice(10);
    byId('panel-notes').textContent = lines.slice(stem+1, options).join('\n').replace('Necessary definitions and panel overview:', '').trim();
    byId('sample-context').hidden = !byId('panel-notes').textContent;
    byId('sample-context').open = false;
    byId('sample-id').textContent = q.id;
    byId('sample-kind').textContent = q.task === 'parallel_integration' ? 'Parallel integration' : 'Dependent query';
    byId('sample-image-link').href = byId('sample-image').src = 'samples/' + q.image;
    byId('sample-image').alt = alt;
    byId('image-credit').href = 'https://doi.org/' + doi;
    byId('image-credit').textContent = credit;
    byId('feedback').textContent = '';
    const container = byId('options');
    container.replaceChildren();
    for (const option of lines.slice(options)) {
      const button = document.createElement('button');
      const letter = document.createElement('b');
      letter.textContent = option[0];
      button.append(letter, document.createTextNode(option.slice(3)));
      button.setAttribute('aria-pressed', 'false');
      button.onclick = () => {
        for (const b of container.children) b.setAttribute('aria-pressed', String(b === button));
        byId('feedback').textContent = option[0] === answers[q.id] ? 'Correct.' : 'Reference answer: ' + answers[q.id] + '.';
      };
      container.append(button);
    }
  }
  display();
  picker.disabled = false;
  picker.onchange = display;
}
loadSamples().catch(() => { byId('feedback').textContent = 'View the sample files on GitHub to try this question.'; });

const models = Array.from(document.querySelectorAll('tbody tr'), tr => {
  const [name, overall, answer, joint] = Array.from(tr.cells, cell => cell.textContent);
  return {name, overall: Number(overall), answer: Number(answer), joint: Number(joint)};
});
function drawChart() {
  const metric = byId('metric').value;
  const n = metric === 'overall' ? '2,650 main questions' : '251 diagnostic questions';
  byId('chart-note').textContent = 'Top five of 15 models · ' + n + ' · 0–100% scale';
  const ranking = byId('ranking');
  ranking.replaceChildren();
  for (const model of [...models].sort((a, b) => b[metric] - a[metric]).slice(0, 5)) {
    const row = document.createElement('div');
    row.className = 'bar-row';
    const name = document.createElement('span');
    name.textContent = model.name;
    const track = document.createElement('span');
    track.className = 'track';
    const bar = document.createElement('i');
    bar.style.width = model[metric] + '%';
    track.append(bar);
    const score = document.createElement('b');
    score.textContent = model[metric].toFixed(2) + '%';
    row.append(name, track, score);
    ranking.append(row);
  }
}
drawChart();
byId('chartbox').hidden = false;
byId('metric').onchange = drawChart;

const commands = byId('commands');
const modelCommands = commands.textContent;
const cloneCommands = modelCommands.split('\n').slice(0, 2).join('\n');
byId('quickstart').onchange = event => {
  const fixture = event.target.value === 'fixture';
  commands.textContent = fixture
    ? cloneCommands + '\npython3 -m evaluation score --predictions samples/example-predictions.jsonl'
    : modelCommands;
  byId('run-hint').textContent = fixture ? 'Example predictions · 2/4 correct (50%)' : 'Use the URL and model name of your vision server.';
};
