document.addEventListener('DOMContentLoaded', () => {
    // --- Mobile Navigation ---
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navToggle.classList.toggle('active');
            navLinks.classList.toggle('open');
        });

        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navToggle.classList.remove('active');
                navLinks.classList.remove('open');
            });
        });

        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
                navToggle.classList.remove('active');
                navLinks.classList.remove('open');
            }
        });
    }

    // --- Contact Form ---
    const contactForm = document.getElementById('contactForm');

    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(contactForm);
            const data = {
                nombre: formData.get('nombre'),
                email: formData.get('email'),
                mensaje: formData.get('mensaje')
            };

            const submitBtn = contactForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Enviando...';
            submitBtn.disabled = true;

            try {
                const response = await fetch('/api/contact', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();

                if (response.ok) {
                    alert('Mensaje enviado con exito! Nos pondremos en contacto pronto.');
                    contactForm.reset();
                } else {
                    alert('Error: ' + (result.error || 'No se pudo enviar el mensaje.'));
                }
            } catch (error) {
                console.error('Error al enviar:', error);
                alert('No se pudo conectar con el servidor.');
            } finally {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    // --- 3D Card & QR ---
    const card3d = document.getElementById('card3d');
    const cardContainer = document.getElementById('cardContainer');
    const btnFlipCard = document.getElementById('btnFlipCard');
    const btnDownloadVCard = document.getElementById('btnDownloadVCard');
    const qrContainer = document.getElementById('qrCodeCanvas');

    // vCard data
    const vCardData = `BEGIN:VCARD
VERSION:3.0
N:Bailey;Zumaikira;;;
FN:Zumaikira Bailey
ORG:Consultoria Psicologica
TITLE:Psicologa (C.I.P. 8362)
TEL;TYPE=CELL,VOICE:+5076235281
EMAIL;TYPE=INTERNET:Zumaikirabailey98@gmail.com
ADR;TYPE=WORK:;;Atlantic plaza, primer piso local 127, oficina #224;Panama;;;
NOTE:Tu bienestar mental es tu mejor version. Atencion a ninos, adolescentes y adultos.
END:VCARD`;

    // Generate QR
    if (qrContainer && typeof qrcode !== 'undefined') {
        try {
            const typeNumber = 0;
            const errorCorrectionLevel = 'M';
            const qr = qrcode(typeNumber, errorCorrectionLevel);
            qr.addData(vCardData);
            qr.make();
            qrContainer.innerHTML = qr.createImgTag(4, 8);
        } catch (err) {
            console.error("Error al generar codigo QR:", err);
        }
    }

    // 3D Tilt Effect
    if (cardContainer && card3d) {
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

        if (!isTouchDevice) {
            cardContainer.addEventListener('mousemove', (e) => {
                const rect = cardContainer.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                
                const isFlipped = card3d.classList.contains('flipped');
                const rotateY = isFlipped ? 180 + (x / 15) : (x / 15);
                const rotateX = -y / 15;

                card3d.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
            });

            cardContainer.addEventListener('mouseleave', () => {
                const isFlipped = card3d.classList.contains('flipped');
                card3d.style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)';
            });
        }

        cardContainer.addEventListener('click', () => {
            card3d.classList.toggle('flipped');
        });
    }

    // Flip button
    if (btnFlipCard && card3d) {
        btnFlipCard.addEventListener('click', (e) => {
            e.stopPropagation();
            card3d.classList.toggle('flipped');
        });
    }

    // Download vCard
    if (btnDownloadVCard) {
        btnDownloadVCard.addEventListener('click', (e) => {
            e.stopPropagation();
            const blob = new Blob([vCardData], { type: 'text/vcard;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'Zumaikira_Bailey_Psicologa.vcf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    // Smooth scroll offset for sticky nav
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            const targetId = anchor.getAttribute('href');
            if (targetId === '#') return;
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                const navHeight = document.querySelector('.site-nav')?.offsetHeight || 56;
                const targetPos = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
                window.scrollTo({ top: targetPos, behavior: 'smooth' });
            }
        });
    });
});
