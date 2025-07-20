import streamlit as st
import pandas as pd
import json
from database import (
    get_governorate_admin_data,
    get_governorate_surveys,
    get_governorate_employees,
    update_survey,
    get_survey_fields,
    update_user,
    get_user_allowed_surveys,
    update_user_allowed_surveys,
    get_response_info,
    get_response_details,
    update_response_detail
)

def show_governorate_admin_dashboard():
    if st.session_state.get('role') != 'governorate_admin':
        st.error("غير مصرح لك بالوصول إلى هذه الصفحة")
        return
    
    gov_data = get_governorate_admin_data(st.session_state.user_id)
    if not gov_data:
        st.error("حسابك غير مرتبط بأي محافظة. يرجى التواصل مع مسؤول النظام.")
        return
    
    governorate_id, governorate_name, description = gov_data
    
    st.set_page_config(layout="wide")
    st.title(f"لوحة تحكم محافظة {governorate_name}")
    st.markdown(f"**وصف المحافظة:** {description}")
    
    tab1, tab2, tab3 = st.tabs([
        "📋 إدارة الاستبيانات",
        "📊 عرض البيانات",
        "👥 إدارة الموظفين"
    ])
    
    with tab1:
        manage_governorate_surveys(governorate_id, governorate_name)
    with tab2:
        view_governorate_data(governorate_id, governorate_name)
    with tab3:
        manage_governorate_employees(governorate_id, governorate_name)

def manage_governorate_surveys(governorate_id, governorate_name):
    st.subheader(f"إدارة استبيانات محافظة {governorate_name}")
    
    if 'editing_survey' in st.session_state:
        edit_governorate_survey(st.session_state.editing_survey, governorate_id)
        return
    
    surveys = get_governorate_surveys(governorate_id)
    if not surveys:
        st.info("لا توجد استبيانات لهذه المحافظة")
        return
    
    df = pd.DataFrame(survey[1:] for survey in surveys)
    df.columns = ["اسم الاستبيان", "تاريخ الإنشاء", "الحالة"]
    df["الحالة"] = df["الحالة"].apply(lambda x: "مفعل" if x else "غير مفعل")

    st.dataframe(df, use_container_width=True)
    
    selected_survey = st.selectbox(
        "اختر استبيان للتحكم",
        surveys,
        format_func=lambda x: x[1]
    )
    
    survey_id = selected_survey[0]
    
    if st.button("تعديل حالة الاستبيان", key=f"edit_{survey_id}"):
        st.session_state.editing_survey = survey_id
        st.rerun()

def edit_governorate_survey(survey_id, governorate_id):
    st.subheader("تعديل حالة الاستبيان")
    
    try:
        survey = st.session_state.supabase.table('Surveys').select('survey_name, is_active').eq('survey_id', survey_id).execute().data
        
        with st.form(f"edit_survey_{survey_id}"):
            st.text_input("اسم الاستبيان", value=survey[0]['survey_name'], disabled=True)
            is_active = st.checkbox("مفعل", value=bool(survey[0]['is_active']))
            
            st.info("ملاحظة: مسؤول المحافظة يمكنه فقط تغيير حالة تفعيل الاستبيان")
            
            col1, col2 = st.columns(2)
            with col1:
                save_btn = st.form_submit_button("💾 حفظ التعديلات")
                if save_btn:
                    st.session_state.supabase.table('Surveys').update({
                        'is_active': is_active
                    }).eq('survey_id', survey_id).execute()
                    st.success("تم تحديث حالة الاستبيان بنجاح")
                    del st.session_state.editing_survey
                    st.rerun()
            
            with col2:
                cancel_btn = st.form_submit_button("❌ إلغاء")
                if cancel_btn:
                    del st.session_state.editing_survey
                    st.rerun()
    
    except Exception as e:
        st.error(f"حدث خطأ في قاعدة البيانات: {str(e)}")

def view_governorate_data(governorate_id, governorate_name):
    st.header(f"بيانات محافظة {governorate_name}")
    
    surveys = get_governorate_surveys(governorate_id)
    if not surveys:
        st.info("لا توجد استبيانات لعرض البيانات")
        return
    
    selected_survey = st.selectbox(
        "اختر استبيان",
        surveys,
        format_func=lambda x: x[1],
        key="survey_select"
    )
    
    if selected_survey:
        view_survey_responses(selected_survey[0], governorate_id)

def view_survey_responses(survey_id, governorate_id):
    try:
        survey = st.session_state.supabase.table('Surveys').select('survey_name').eq('survey_id', survey_id).execute().data
        st.subheader(f"إجابات استبيان {survey[0]['survey_name']}")
        
        responses = st.session_state.supabase.table('Responses').select('''
            response_id, 
            Users(username), 
            HealthAdministrations(admin_name, Governorates(governorate_name)),
            submission_date, 
            is_completed
        ''').eq('survey_id', survey_id).eq('HealthAdministrations.governorate_id', governorate_id).execute().data
        
        if not responses:
            st.info("لا توجد إجابات مسجلة لهذا الاستبيان في محافظتك")
            return
        
        total = len(responses)
        completed = sum(1 for r in responses if r['is_completed'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("إجمالي الإجابات", total)
        col2.metric("الإجابات المكتملة", completed)
        col3.metric("نسبة الإكمال", f"{round((completed/total)*100)}%")
        
        df = pd.DataFrame(
            [(r['response_id'], r['Users']['username'], 
              r['HealthAdministrations']['admin_name'], 
              r['HealthAdministrations']['Governorates']['governorate_name'],
              r['submission_date'], 
              "✔️" if r['is_completed'] else "✖️") 
             for r in responses],
            columns=["ID", "المستخدم", "الإدارة الصحية", "المحافظة", "التاريخ", "الحالة"]
        )
        
        st.dataframe(df, use_container_width=True)
        
        selected_response_id = st.selectbox(
            "اختر إجابة لعرض وتعديل تفاصيلها",
            options=[r['response_id'] for r in responses],
            format_func=lambda x: f"إجابة #{x}",
            key=f"response_select_{survey_id}_{governorate_id}"
        )

        if selected_response_id:
            response_info = get_response_info(selected_response_id)
            if response_info:
                st.subheader(f"تفاصيل الإجابة #{selected_response_id}")
                st.markdown(f"""
                **الاستبيان:** {response_info[1]}  
                **المستخدم:** {response_info[2]}  
                **الإدارة الصحية:** {response_info[3]}  
                **المحافظة:** {response_info[4]}  
                **تاريخ التقديم:** {response_info[5]}
                """)
                
                details = get_response_details(selected_response_id)
                updates = {}
                
                with st.form(key=f"edit_response_{survey_id}_{governorate_id}_{selected_response_id}"):
                    for detail in details:
                        detail_id, field_id, label, field_type, options, answer = detail
                        
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.markdown(f"**{label}**")
                        with col2:
                            if field_type == 'dropdown':
                                options_list = json.loads(options) if options else []
                                new_value = st.selectbox(
                                    f"تعديل {label}",
                                    options_list,
                                    index=options_list.index(answer) if answer in options_list else 0,
                                    key=f"edit_dropdown_{detail_id}_{selected_response_id}"
                                )
                            else:
                                new_value = st.text_input(
                                    f"تعديل {label}",
                                    value=answer,
                                    key=f"edit_input_{detail_id}_{selected_response_id}"
                                )
                            
                            if new_value != answer:
                                updates[detail_id] = new_value
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 حفظ جميع التعديلات"):
                            if updates:
                                success_count = 0
                                for detail_id, new_value in updates.items():
                                    if update_response_detail(detail_id, new_value):
                                        success_count += 1
                                
                                if success_count == len(updates):
                                    st.success("تم تحديث جميع التعديلات بنجاح")
                                else:
                                    st.error(f"تم تحديث {success_count} من أصل {len(updates)} تعديلات")
                                st.rerun()
                            else:
                                st.info("لم تقم بإجراء أي تعديلات")
                    with col2:
                        if st.form_submit_button("❌ إلغاء التعديلات"):
                            st.rerun()
        
    except Exception as e:
        st.error(f"حدث خطأ في قاعدة البيانات: {str(e)}")

def manage_governorate_employees(governorate_id, governorate_name):
    st.header(f"إدارة موظفي محافظة {governorate_name}")
    
    employees = get_governorate_employees(governorate_id)
    if not employees:
        st.info("لا يوجد موظفون مسجلون لهذه المحافظة")
        return
    
    for emp in employees:
        user_id, username, admin_name = emp
        
        with st.expander(f"{username} - {admin_name}"):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                **اسم المستخدم:** {username}  
                **الإدارة الصحية:** {admin_name}
                """)
            
            with col2:
                if st.button("تعديل", key=f"edit_btn_{user_id}"):
                    st.session_state.editing_employee = user_id
    
    if 'editing_employee' in st.session_state:
        edit_employee(st.session_state.editing_employee, governorate_id)

def edit_employee(user_id, governorate_id):
    st.subheader("تعديل بيانات الموظف")
    
    try:
        employee = st.session_state.supabase.table('Users').select('''
            username, assigned_region, HealthAdministrations(admin_name)
        ''').eq('user_id', user_id).execute().data
        
        if not employee:
            st.error("الموظف غير موجود")
            del st.session_state.editing_employee
            return
        
        employee = employee[0]
        health_admins = st.session_state.supabase.table('HealthAdministrations').select('admin_id, admin_name').eq('governorate_id', governorate_id).order('admin_name').execute().data
        
        surveys = get_governorate_surveys(governorate_id)
        allowed_surveys = get_user_allowed_surveys(user_id)
        allowed_survey_ids = [s[0] for s in allowed_surveys]
        
        survey_ids = [s[0] for s in surveys]
        valid_allowed_survey_ids = [sid for sid in allowed_survey_ids if sid in survey_ids]
        
        with st.form(f"edit_employee_{user_id}"):
            st.text_input("اسم المستخدم", value=employee['username'], disabled=True)
            
            selected_admin = st.selectbox(
                "الإدارة الصحية",
                options=[a['admin_id'] for a in health_admins],
                index=[a['admin_id'] for a in health_admins].index(employee['assigned_region']) if health_admins else 0,
                format_func=lambda x: next(a['admin_name'] for a in health_admins if a['admin_id'] == x)
            )
            
            if surveys:
                selected_surveys = st.multiselect(
                    "الاستبيانات المسموح بها",
                    options=[s[0] for s in surveys],
                    default=valid_allowed_survey_ids,
                    format_func=lambda x: next(s[1] for s in surveys if s[0] == x)
                )
            else:
                st.info("لا توجد استبيانات متاحة لهذه المحافظة")
                selected_surveys = []
            
            col1, col2 = st.columns(2)
            with col1:
                submit_btn = st.form_submit_button("💾 حفظ التعديلات")
            with col2:
                cancel_btn = st.form_submit_button("❌ إلغاء")
            
            if submit_btn:
                update_user(user_id, employee['username'], 'employee', selected_admin)
                
                if update_user_allowed_surveys(user_id, selected_surveys):
                    st.success("تم تحديث بيانات الموظف بنجاح")
                    del st.session_state.editing_employee
                    st.rerun()
            
            if cancel_btn:
                del st.session_state.editing_employee
                st.rerun()
    
    except Exception as e:
        st.error(f"حدث خطأ في قاعدة البيانات: {str(e)}")