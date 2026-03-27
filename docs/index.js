const cards = document.querySelectorAll('.card');

for (const card of cards) {
  card.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      card.click();
    }
  });
}
