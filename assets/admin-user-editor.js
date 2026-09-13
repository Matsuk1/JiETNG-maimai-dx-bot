    let editingUserOriginalData = {};

    function editUser(userId) {
      // 从页面中获取用户数据
      const userDataElement = document.getElementById('data-' + userId);
      const jsonStr = userDataElement.querySelector('pre').textContent;
      editingUserOriginalData = JSON.parse(jsonStr);

      document.getElementById('edit-user-id').value = userId;
      document.getElementById('edit-user-data').value = jsonStr;
      document.getElementById('editUserModal').classList.add('show');
    }

    function closeEditModal() {
      document.getElementById('editUserModal').classList.remove('show');
    }

    function saveUserData(event) {
      event.preventDefault();

      const userId = document.getElementById('edit-user-id').value;
      const userDataStr = document.getElementById('edit-user-data').value;

      // Validate JSON
      try {
        const userData = JSON.parse(userDataStr);
        if (!userData || typeof userData !== 'object' || Array.isArray(userData)) {
          throw new Error('User data must be a JSON object');
        }
        const changedFields = Object.fromEntries(
          Object.entries(userData).filter(([key, value]) =>
            !Object.prototype.hasOwnProperty.call(editingUserOriginalData, key) ||
            JSON.stringify(value) !== JSON.stringify(editingUserOriginalData[key])
          )
        );
        if (Object.keys(changedFields).length === 0) {
          closeEditModal();
          return;
        }

        if (!confirm('Save changes for user ' + userId + '?')) {
          return;
        }

        fetch('/admin/edit_user', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            user_id: userId,
            user_data: changedFields
          })
        })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            alert('✅ User data saved successfully!');
            closeEditModal();
            location.reload();
          } else {
            alert('❌ Error: ' + (data.message || 'Unknown error'));
          }
        })
        .catch(err => {
          alert('❌ Network error: ' + err);
        });
      } catch (e) {
        alert('❌ Invalid JSON format!\n\n' + e.message);
      }
    }

