document.addEventListener('DOMContentLoaded', () => {
    const savedSkillsList = document.getElementById('saved-skills-list');

    async function loadSavedSkills() {
        const response = await fetch('/api/skills');
        if (response.ok) {
            const skills = await response.json();
            savedSkillsList.innerHTML = '';
            if (skills.length === 0) {
                savedSkillsList.innerHTML = '<p>You have no saved skills yet.</p>';
                return;
            }
            const ul = document.createElement('ul');
            ul.className = 'skills-list';
            skills.forEach(skill => {
                const li = document.createElement('li');
                li.className = 'skills-list__item';
                li.innerHTML = `
                    <p class="skills-list__text">${skill.skill_description}</p>
                    <button class="btn-delete" data-skill-id="${skill.id}">Delete</button>
                `;
                ul.appendChild(li);
            });
            savedSkillsList.appendChild(ul);
        } else {
            savedSkillsList.innerHTML = '<p>Could not load saved skills.</p>';
        }
    }

    savedSkillsList.addEventListener('click', async (e) => {
        if (e.target.classList.contains('btn-delete')) {
            const skillId = e.target.dataset.skillId;
            const response = await fetch(`/api/skills/${skillId}`, {
                method: 'DELETE',
            });
            if (response.ok) {
                loadSavedSkills();
            }
        }
    });

    loadSavedSkills();
});
