import streamlit as st
from datetime import datetime, timedelta 
from auth import authenticate, logout
from admin_views import show_admin_dashboard
from employee_views import show_employee_dashboard
from governorate_admin_views import show_governorate_admin_dashboard
from database import get_user_role
from supabase import create_client, Client


def main():
    st.set_page_config(page_title="نظام إدارة الاستبيانات", page_icon="📋", layout="wide")
    
    # التحقق من حالة الجلسة
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        
    if authenticate():  # إذا كان مسجل الدخول
        # تحديث وقت النشاط عند كل تفاعل
        st.session_state.last_activity = datetime.now()
        
        # عرض واجهة المستخدم حسب الدور
        user_role = get_user_role(st.session_state.user_id)
        
        # زر تسجيل الخروج
        st.sidebar.button("تسجيل الخروج", on_click=logout)
        
        if user_role == 'admin':
            show_admin_dashboard()
        elif user_role == 'governorate_admin':
            show_governorate_admin_dashboard()
        else:
            show_employee_dashboard()

if __name__ == "__main__":
    main()
