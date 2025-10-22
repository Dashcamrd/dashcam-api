# Retool Admin Dashboard Setup Guide

## 🚀 Complete Guide for Dashcam Management Admin Interface

### **Step 1: Retool Account Setup**

1. **Go to:** https://retool.com
2. **Sign up** with your email
3. **Choose the free plan** (perfect for getting started)
4. **Verify your email**

### **Step 2: Database Connection**

Since direct database connection might be restricted, we'll use your API endpoints instead.

#### **Option A: API Connection (Recommended)**
1. **Click "Create new app"**
2. **Click "Add a resource"**
3. **Select "REST API"**
4. **Enter API details:**
   ```
   Base URL: https://dashcam-api.onrender.com
   Authentication: Bearer Token
   ```

#### **Option B: Direct Database (If Available)**
If you can get external database access:
```
Host: shortline.proxy.rlwy.net
Port: 58339
Database: railway
Username: root
Password: DHwoWoogDNQzVkoCJvJPPAmpAQdwdIwy
SSL Mode: Required
```

### **Step 3: Build User Management Interface**

#### **3.1 User List Table**
1. **Add a Table component**
2. **Configure data source:**
   ```javascript
   // Query: getUsers
   GET https://dashcam-api.onrender.com/admin/users
   Headers: Authorization: Bearer {{adminToken}}
   ```
3. **Configure columns:**
   - ID
   - Invoice Number
   - Name
   - Email
   - Created At
   - Actions (Edit/Delete buttons)

#### **3.2 Add User Form**
1. **Add a Modal component**
2. **Add form fields:**
   - Invoice Number (Text Input)
   - Password (Password Input)
   - Name (Text Input)
   - Email (Text Input)
3. **Add submit button with query:**
   ```javascript
   // Query: createUser
   POST https://dashcam-api.onrender.com/admin/users
   Headers: 
     Authorization: Bearer {{adminToken}}
     Content-Type: application/json
   Body:
   {
     "invoice_no": "{{invoiceNo.value}}",
     "password": "{{password.value}}",
     "name": "{{name.value}}",
     "email": "{{email.value}}"
   }
   ```

#### **3.3 Edit User Form**
1. **Duplicate the Add User form**
2. **Pre-populate fields with selected user data**
3. **Update submit query to use PUT method**

### **Step 4: Build Device Management Interface**

#### **4.1 Device List Table**
1. **Add a Table component**
2. **Configure data source:**
   ```javascript
   // Query: getDevices
   GET https://dashcam-api.onrender.com/admin/devices/unassigned
   Headers: Authorization: Bearer {{adminToken}}
   ```
3. **Configure columns:**
   - Device ID
   - Name
   - Brand
   - Model
   - Status
   - Assigned User
   - Actions

#### **4.2 Add Device Form**
1. **Add a Modal component**
2. **Add form fields:**
   - Device ID (Text Input)
   - Device Name (Text Input)
   - Brand (Text Input)
   - Model (Text Input)
   - Organization ID (Text Input)
3. **Add submit button with query:**
   ```javascript
   // Query: createDevice
   POST https://dashcam-api.onrender.com/admin/devices/assign
   Headers: 
     Authorization: Bearer {{adminToken}}
     Content-Type: application/json
   Body:
   {
     "device_id": "{{deviceId.value}}",
     "device_name": "{{deviceName.value}}",
     "user_id": {{selectedUserId}},
     "org_id": "{{orgId.value}}"
   }
   ```

### **Step 5: Build Device Assignment Interface**

#### **5.1 Assignment Table**
1. **Add a Table component**
2. **Configure data source:**
   ```javascript
   // Query: getAssignments
   SELECT d.*, u.name as user_name, u.invoice_no 
   FROM devices d 
   JOIN users u ON d.assigned_user_id = u.id
   ```
3. **Configure columns:**
   - Device ID
   - Device Name
   - Assigned User
   - Invoice Number
   - Status
   - Actions

#### **5.2 Reassign Device Form**
1. **Add a Modal component**
2. **Add form fields:**
   - Device (Dropdown - populated from devices)
   - New User (Dropdown - populated from users)
3. **Add submit button with query:**
   ```javascript
   // Query: reassignDevice
   PUT https://dashcam-api.onrender.com/admin/devices/assign
   Headers: 
     Authorization: Bearer {{adminToken}}
     Content-Type: application/json
   Body:
   {
     "device_id": "{{selectedDevice}}",
     "user_id": {{selectedUser}}
   }
   ```

### **Step 6: Build System Dashboard**

#### **6.1 Statistics Cards**
1. **Add Stat components (4 cards):**
   - Total Users
   - Total Devices
   - Online Devices
   - Assigned Devices

2. **Configure data sources:**
   ```javascript
   // Query: getStats
   GET https://dashcam-api.onrender.com/admin/dashboard/overview
   Headers: Authorization: Bearer {{adminToken}}
   ```

#### **6.2 Charts and Graphs**
1. **Add Chart components:**
   - Users by Month (Line Chart)
   - Device Status Distribution (Pie Chart)
   - Assignment Status (Bar Chart)

#### **6.3 Recent Activity Table**
1. **Add a Table component**
2. **Show recent user logins, device assignments, etc.**

### **Step 7: Authentication Setup**

#### **7.1 Admin Login**
1. **Add a Form component**
2. **Add fields:**
   - Username (Text Input)
   - Password (Password Input)
3. **Add login button with query:**
   ```javascript
   // Query: adminLogin
   POST https://dashcam-api.onrender.com/auth/login
   Headers: Content-Type: application/json
   Body:
   {
     "invoice_no": "{{username.value}}",
     "password": "{{password.value}}"
   }
   ```

#### **7.2 Token Management**
1. **Store token in Retool's app state**
2. **Use token in all API requests**
3. **Add logout functionality**

### **Step 8: Navigation and Layout**

#### **8.1 Sidebar Navigation**
1. **Add a Container component**
2. **Add navigation items:**
   - Dashboard
   - Users
   - Devices
   - Assignments
   - Settings

#### **8.2 Page Layout**
1. **Create separate pages for each section**
2. **Use Retool's page navigation**
3. **Add breadcrumbs**

### **Step 9: Advanced Features**

#### **9.1 Search and Filtering**
1. **Add search inputs to tables**
2. **Implement filtering logic**
3. **Add sorting capabilities**

#### **9.2 Bulk Operations**
1. **Add checkboxes to tables**
2. **Implement bulk delete/assign operations**
3. **Add confirmation modals**

#### **9.3 Export Functionality**
1. **Add export buttons**
2. **Export data to CSV/Excel**
3. **Generate reports**

### **Step 10: Testing and Deployment**

#### **10.1 Test All Features**
1. **Test user creation**
2. **Test device management**
3. **Test assignment workflow**
4. **Test dashboard statistics**

#### **10.2 User Management**
1. **Create admin user accounts**
2. **Set up permissions**
3. **Train admin users**

## 🎯 Quick Start Checklist

- [ ] Create Retool account
- [ ] Set up API connection
- [ ] Build user management interface
- [ ] Build device management interface
- [ ] Build assignment interface
- [ ] Build dashboard
- [ ] Set up authentication
- [ ] Test all features
- [ ] Deploy and share with team

## 📱 API Endpoints Reference

### **User Management:**
- `GET /admin/users` - List all users
- `POST /admin/users` - Create new user
- `PUT /admin/users/{id}` - Update user
- `DELETE /admin/users/{id}` - Delete user

### **Device Management:**
- `GET /admin/devices/unassigned` - Get unassigned devices
- `POST /admin/devices/assign` - Assign device to user
- `PUT /admin/devices/assign` - Reassign device
- `DELETE /admin/devices/{id}` - Delete device

### **Dashboard:**
- `GET /admin/dashboard/overview` - Get system statistics
- `GET /admin/config/system` - Get system configuration

## 🔧 Troubleshooting

### **Common Issues:**
1. **API Connection Failed:** Check API URL and authentication
2. **Data Not Loading:** Verify API endpoints and headers
3. **Forms Not Submitting:** Check request body format
4. **Authentication Issues:** Verify token format and expiration

### **Support:**
- Retool Documentation: https://docs.retool.com
- API Documentation: https://dashcam-api.onrender.com/docs
- GitHub Repository: https://github.com/Dashcamrd/dashcam-api

## 🚀 Next Steps

1. **Complete Retool setup**
2. **Test admin interface**
3. **Create admin user accounts**
4. **Start building Flutter customer app**
5. **Test end-to-end workflow**

---

**Your admin dashboard will be ready in 1-2 days with this guide!** 🎉


