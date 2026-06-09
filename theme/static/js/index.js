// mobile dropdown
function toggleMobileProducts() {
    const menu = document.getElementById('mobileProducts');
    menu.classList.toggle('hidden');
    
    const arrow = document.getElementById('arrowIcon').innerHTML = (menu.classList.contains('hidden') == true) ? '▼' : '▲';
}