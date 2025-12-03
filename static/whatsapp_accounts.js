// WhatsApp Account Management JavaScript

let currentAccounts = [];

// Load accounts on page load
async function loadWhatsAppAccounts() {
    try {
        const response = await fetch('/api/whatsapp/accounts');
        const data = await response.json();

        if (data.success) {
            currentAccounts = data.accounts;
            renderAccountsList();
        }
    } catch (error) {
        console.error('Error loading accounts:', error);
    }
}

// Render accounts list
function renderAccountsList() {
    const accountsList = document.getElementById('accountsList');

    if (currentAccounts.length === 0) {
        accountsList.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #718096; font-size: 14px;">
                Keine Accounts vorhanden. Erstellen Sie Ihren ersten Account!
            </div>
        `;
        return;
    }

    accountsList.innerHTML = currentAccounts.map(account => `
        <div style="background: #fff; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 1;">
                <div style="font-weight: bold; color: #2d3748; margin-bottom: 5px;">
                    ${account.account_name}
                    ${account.is_logged_in ? '<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">✓ Verbunden</span>' : '<span style="background: #6b7280; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">Nicht verbunden</span>'}
                </div>
                <div style="font-size: 13px; color: #718096;">
                    ${account.phone_number || 'Noch keine Nummer'} |
                    ${account.messages_sent_today}/${account.daily_message_limit} Nachrichten heute
                </div>
            </div>
            <div style="display: flex; gap: 8px;">
                <button onclick="setupAccountWhatsApp(${account.id})" style="background: #3b82f6; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;">
                    🚀 Setup
                </button>
                <button onclick="deleteAccountConfirm(${account.id}, '${account.account_name}')" style="background: #ef4444; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;">
                    🗑️
                </button>
            </div>
        </div>
    `).join('');
}

// Show add account modal
function showAddAccountModal() {
    const modal = document.getElementById('addAccountModal');
    modal.style.display = 'flex';
}

// Hide add account modal
function hideAddAccountModal() {
    const modal = document.getElementById('addAccountModal');
    modal.style.display = 'none';
    document.getElementById('newAccountName').value = '';
    document.getElementById('newAccountLimit').value = '100';
}

// Create new account
async function createAccount() {
    const accountName = document.getElementById('newAccountName').value.trim();
    const dailyLimit = parseInt(document.getElementById('newAccountLimit').value);

    if (!accountName) {
        alert('Bitte geben Sie einen Account-Namen ein!');
        return;
    }

    try {
        const response = await fetch('/api/whatsapp/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_name: accountName, daily_limit: dailyLimit })
        });

        const data = await response.json();

        if (data.success) {
            hideAddAccountModal();
            loadWhatsAppAccounts();
            alert(`Account "${accountName}" erfolgreich erstellt!`);
        } else {
            alert(`Fehler: ${data.message}`);
        }
    } catch (error) {
        alert(`Fehler beim Erstellen: ${error.message}`);
    }
}

// Setup WhatsApp for specific account
async function setupAccountWhatsApp(accountId) {
    try {
        const response = await fetch(`/api/whatsapp/accounts/${accountId}/setup`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            console.log(`Setup started for account ${accountId}`);
        } else {
            alert(`Setup Fehler: ${data.message}`);
        }
    } catch (error) {
        alert(`Fehler beim Setup: ${error.message}`);
    }
}

// Delete account with confirmation
function deleteAccountConfirm(accountId, accountName) {
    if (confirm(`Möchten Sie den Account "${accountName}" wirklich löschen?\n\nDies kann nicht rückgängig gemacht werden!`)) {
        deleteAccount(accountId);
    }
}

// Delete account
async function deleteAccount(accountId) {
    try {
        const response = await fetch(`/api/whatsapp/accounts/${accountId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            loadWhatsAppAccounts();
            alert('Account erfolgreich gelöscht!');
        } else {
            alert(`Fehler beim Löschen: ${data.message}`);
        }
    } catch (error) {
        alert(`Fehler beim Löschen: ${error.message}`);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadWhatsAppAccounts();

    // Refresh accounts every 30 seconds
    setInterval(loadWhatsAppAccounts, 30000);

    // Socket.IO event listeners for real-time updates
    if (typeof socket !== 'undefined') {
        // Listen for account status changes (after QR scan login)
        socket.on('whatsapp_status', function(data) {
            console.log('WhatsApp status event:', data);
            if (data.status === 'ready') {
                // Reload account list to show updated "Verbunden" status
                loadWhatsAppAccounts();
            }
        });

        // Listen for QR code ready event
        socket.on('whatsapp_qr_ready', function(data) {
            console.log('WhatsApp QR ready event:', data);
            // Reload account list in case status changed
            loadWhatsAppAccounts();
        });

        // Listen for campaign events to update account stats
        socket.on('whatsapp_campaign_completed', function(data) {
            console.log('Campaign completed:', data);
            // Reload accounts to show updated message counts
            loadWhatsAppAccounts();
        });
    }
});
