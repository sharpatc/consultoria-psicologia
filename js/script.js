document.addEventListener('DOMContentLoaded', () => {
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
                    alert('¡Mensaje enviado con éxito! Nos pondremos en contacto pronto.');
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

    // --- Lógica de Tarjeta 3D y Generador QR ---
    const card3d = document.getElementById('card3d');
    const cardContainer = document.getElementById('cardContainer');
    const btnFlipCard = document.getElementById('btnFlipCard');
    const btnDownloadVCard = document.getElementById('btnDownloadVCard');
    const qrContainer = document.getElementById('qrCodeCanvas');

    // 1. Datos vCard para Zumaikira Bailey
    const vCardData = `BEGIN:VCARD
VERSION:3.0
N:Bailey;Zumaikira;;;
FN:Zumaikira Bailey
ORG:Consultoría Psicológica
TITLE:Psicóloga (C.I.P. 8362)
TEL;TYPE=CELL,VOICE:+5076235281
EMAIL;TYPE=INTERNET:Zumaikirabailey98@gmail.com
ADR;TYPE=WORK:;;Atlantic plaza, primer piso local 127, oficina #224;Panamá;;;
NOTE:Tu bienestar mental es tu mejor versión. Atención a niños, adolescentes y adultos.
END:VCARD`;

    // 2. Generar el Código QR usando qrcode-generator
    if (qrContainer && typeof qrcode !== 'undefined') {
        try {
            const typeNumber = 0; // Auto detect
            const errorCorrectionLevel = 'M';
            const qr = qrcode(typeNumber, errorCorrectionLevel);
            qr.addData(vCardData);
            qr.make();
            qrContainer.innerHTML = qr.createImgTag(4, 8); // Cell size 4, margin 8
        } catch (err) {
            console.error("Error al generar código QR:", err);
        }
    }

    // 3. Efecto 3D Tilt con el Mouse
    if (cardContainer && card3d) {
        cardContainer.addEventListener('mousemove', (e) => {
            const rect = cardContainer.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            
            // Si no está volteada, inclinación normal. Si está volteada, ajustar Y
            const isFlipped = card3d.classList.contains('flipped');
            const rotateY = isFlipped ? 180 + (x / 15) : (x / 15);
            const rotateX = -y / 15;

            card3d.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        cardContainer.addEventListener('mouseleave', () => {
            const isFlipped = card3d.classList.contains('flipped');
            card3d.style.transform = isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)';
        });

        // 4. Giro al hacer clic en la tarjeta
        cardContainer.addEventListener('click', () => {
            card3d.classList.toggle('flipped');
        });
    }

    // Botón manual de girar
    if (btnFlipCard && card3d) {
        btnFlipCard.addEventListener('click', (e) => {
            e.stopPropagation();
            card3d.classList.toggle('flipped');
        });
    }

    // 5. Descargar vCard (.vcf)
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
});

