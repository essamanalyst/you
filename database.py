import os
from supabase import create_client, Client
from typing import List, Dict, Optional, Tuple, Any, Union
import streamlit as st
from datetime import datetime
import json
from pathlib import Path

try:
    supabase = create_client(
        supabase_url=st.secrets["SUPABASE_URL"],
        supabase_key=st.secrets["SUPABASE_KEY"],
        options={
            "auto_refresh_token": True,
            "persist_session": True,
            "detect_session_in_url": False
        }
    )
except Exception as e:
    st.error(f"فشل تهيئة Supabase: {str(e)}")
    raise

def init_db():
    pass 


def get_user_by_username(username: str) -> Optional[Dict]:
    try:
        response = supabase.table('Users').select('*, HealthAdministrations(admin_name), GovernorateAdmins(Governorates(governorate_name))').eq('username', username).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def get_user_role(user_id: int) -> Optional[str]:
    """الحصول على دور المستخدم"""
    try:
        response = supabase.table('Users').select('role').eq('user_id', user_id).execute()
        return response.data[0]['role'] if response.data else None
    except Exception as e:
        st.error(f"حدث خطأ في جلب دور المستخدم: {str(e)}")
        return None

def add_user(username: str, password: str, role: str, region_id: Optional[int] = None) -> bool:
    """إضافة مستخدم جديد"""
    from auth import hash_password
    try:
        data = {
            'username': username,
            'password_hash': hash_password(password),
            'role': role,
            'assigned_region': region_id
        }
        response = supabase.table('Users').insert(data).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"حدث خطأ في إضافة المستخدم: {str(e)}")
        return False

def update_user(user_id: int, username: str, role: str, region_id: Optional[int] = None) -> bool:
    """تحديث بيانات المستخدم"""
    try:
        data = {
            'username': username,
            'role': role,
            'assigned_region': region_id
        }
        response = supabase.table('Users').update(data).eq('user_id', user_id).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"حدث خطأ في تحديث المستخدم: {str(e)}")
        return False

def get_health_admins() -> List[Tuple[int, str]]:
    """استرجاع جميع الإدارات الصحية"""
    try:
        response = supabase.table('HealthAdministrations').select('admin_id, admin_name').execute()
        return [(item['admin_id'], item['admin_name']) for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب الإدارات الصحية: {str(e)}")
        return []

def get_health_admin_name(admin_id: int) -> str:
    """استرجاع اسم الإدارة الصحية"""
    if admin_id is None:
        return "غير معين"
    
    try:
        response = supabase.table('HealthAdministrations').select('admin_name').eq('admin_id', admin_id).execute()
        return response.data[0]['admin_name'] if response.data else "غير معروف"
    except Exception as e:
        st.error(f"حدث خطأ في جلب اسم الإدارة الصحية: {str(e)}")
        return "خطأ في النظام"

def save_response(survey_id: int, user_id: int, region_id: int, is_completed: bool = False) -> Optional[int]:
    """حفظ استجابة جديدة"""
    try:
        response = supabase.table('Responses').insert({
            'survey_id': survey_id,
            'user_id': user_id,
            'region_id': region_id,
            'is_completed': is_completed
        }).execute()
        return response.data[0]['response_id'] if response.data else None
    except Exception as e:
        st.error(f"حدث خطأ في حفظ الاستجابة: {str(e)}")
        return None

def save_response_detail(response_id: int, field_id: int, answer_value: str) -> bool:
    """حفظ تفاصيل الإجابة"""
    try:
        response = supabase.table('Response_Details').insert({
            'response_id': response_id,
            'field_id': field_id,
            'answer_value': str(answer_value) if answer_value is not None else ""
        }).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"حدث خطأ في حفظ تفاصيل الإجابة: {str(e)}")
        return False

def save_survey(survey_name: str, fields: List[Dict], governorate_ids: List[int]) -> bool:
    try:
        # إدراج الاستبيان الأساسي
        survey_data = {'survey_name': survey_name, 'created_by': st.session_state.user_id}
        survey_response = supabase.table('Surveys').insert(survey_data).execute()
        survey_id = survey_response.data[0]['survey_id']

        # إدراج حقول الاستبيان
        for field in fields:
            field_data = {
                'survey_id': survey_id,
                'field_label': field['field_label'],
                'field_type': field['field_type'],
                'field_options': json.dumps(field.get('field_options', [])),
                'is_required': field.get('is_required', False),
                'field_order': field.get('field_order', 0)
            }
            supabase.table('Survey_Fields').insert(field_data).execute()

        # ربط الاستبيان بالمحافظات
        for gov_id in governorate_ids:
            supabase.table('SurveyGovernorate').insert({'survey_id': survey_id, 'governorate_id': gov_id}).execute()

        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False

def update_last_login(user_id: int):
    """تحديث وقت آخر دخول للمستخدم"""
    try:
        supabase.table('Users').update({
            'last_login': datetime.now().isoformat()
        }).eq('user_id', user_id).execute()
    except Exception as e:
        st.error(f"حدث خطأ في تحديث وقت الدخول: {str(e)}")

def update_user_activity(user_id: int):
    """تحديث نشاط المستخدم"""
    try:
        supabase.table('Users').update({
            'last_activity': datetime.now().isoformat()
        }).eq('user_id', user_id).execute()
    except Exception as e:
        st.error(f"حدث خطأ في تحديث نشاط المستخدم: {str(e)}")

def delete_survey(survey_id: int) -> bool:
    """حذف استبيان وجميع بياناته المرتبطة"""
    try:
        # حذف تفاصيل الإجابات المرتبطة
        supabase.table('Response_Details').delete().in_('response_id', 
            supabase.table('Responses').select('response_id').eq('survey_id', survey_id)
        ).execute()
        
        # حذف الإجابات المرتبطة
        supabase.table('Responses').delete().eq('survey_id', survey_id).execute()
        
        # حذف حقول الاستبيان
        supabase.table('Survey_Fields').delete().eq('survey_id', survey_id).execute()
        
        # حذف روابط المحافظات
        supabase.table('SurveyGovernorate').delete().eq('survey_id', survey_id).execute()
        
        # حذف الاستبيان نفسه
        supabase.table('Surveys').delete().eq('survey_id', survey_id).execute()
        
        st.success("تم حذف الاستبيان بنجاح")
        return True
    except Exception as e:
        st.error(f"حدث خطأ أثناء حذف الاستبيان: {str(e)}")
        return False

def add_health_admin(admin_name: str, description: str, governorate_id: int) -> bool:
    """إضافة إدارة صحية جديدة"""
    try:
        # التحقق من التكرار
        response = supabase.table('HealthAdministrations').select('*').eq('admin_name', admin_name).eq('governorate_id', governorate_id).execute()
        if response.data:
            st.error("هذه الإدارة الصحية موجودة بالفعل في هذه المحافظة!")
            return False
        
        # إضافة الإدارة الجديدة
        supabase.table('HealthAdministrations').insert({
            'admin_name': admin_name,
            'description': description,
            'governorate_id': governorate_id
        }).execute()
        
        st.success(f"تمت إضافة الإدارة الصحية '{admin_name}' بنجاح")
        return True
    except Exception as e:
        st.error(f"حدث خطأ في قاعدة البيانات: {str(e)}")
        return False

def get_governorates_list() -> List[Tuple[int, str]]:
    """استرجاع قائمة المحافظات"""
    try:
        response = supabase.table('Governorates').select('governorate_id, governorate_name').execute()
        return [(item['governorate_id'], item['governorate_name']) for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب المحافظات: {str(e)}")
        return []

def update_survey(survey_id: int, survey_name: str, is_active: bool, fields: List[Dict]) -> bool:
    """تحديث بيانات الاستبيان وحقوله"""
    try:
        # تحديث بيانات الاستبيان الأساسية
        supabase.table('Surveys').update({
            'survey_name': survey_name,
            'is_active': is_active
        }).eq('survey_id', survey_id).execute()
        
        # تحديث الحقول الموجودة أو إضافة جديدة
        for field in fields:
            field_options = json.dumps(field.get('field_options', [])) if field.get('field_options') else None
            
            if 'field_id' in field:  # حقل موجود يتم تحديثه
                supabase.table('Survey_Fields').update({
                    'field_label': field['field_label'],
                    'field_type': field['field_type'],
                    'field_options': field_options,
                    'is_required': field.get('is_required', False)
                }).eq('field_id', field['field_id']).execute()
            else:  # حقل جديد يتم إضافته
                # الحصول على أقصى ترتيب للحقول
                response = supabase.table('Survey_Fields').select('field_order').eq('survey_id', survey_id).order('field_order', desc=True).limit(1).execute()
                max_order = response.data[0]['field_order'] if response.data else 0
                
                supabase.table('Survey_Fields').insert({
                    'survey_id': survey_id,
                    'field_label': field['field_label'],
                    'field_type': field['field_type'],
                    'field_options': field_options,
                    'is_required': field.get('is_required', False),
                    'field_order': max_order + 1
                }).execute()
        
        st.success("تم تحديث الاستبيان بنجاح")
        return True
    except Exception as e:
        st.error(f"حدث خطأ في تحديث الاستبيان: {str(e)}")
        return False

def add_governorate_admin(user_id: int, governorate_id: int) -> bool:
    """إضافة مسؤول محافظة جديد"""
    try:
        supabase.table('GovernorateAdmins').insert({
            'user_id': user_id,
            'governorate_id': governorate_id
        }).execute()
        return True
    except Exception as e:
        st.error(f"خطأ في إضافة مسؤول المحافظة: {str(e)}")
        return False

def get_governorate_admin_data(user_id: int) -> Optional[Tuple]:
    try:
        response = supabase.table('GovernorateAdmins').select('Governorates(governorate_id, governorate_name, description)').eq('user_id', user_id).execute()
        if response.data:
            gov = response.data[0]['Governorates']
            return (gov['governorate_id'], gov['governorate_name'], gov['description'])
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# في database.py
def get_governorate_surveys(governorate_id: int) -> List[Tuple[int, str, str, bool]]:
    try:
        response = supabase.table('SurveyGovernorate').select('Surveys(survey_id, survey_name, created_at, is_active)').eq('governorate_id', governorate_id).execute()
        if not response.data:
            return []
        return [(item['Surveys']['survey_id'], item['Surveys']['survey_name'], 
                item['Surveys']['created_at'], item['Surveys']['is_active']) 
                for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب استبيانات المحافظة: {str(e)}")
        return []

def get_governorate_employees(governorate_id: int) -> List[Tuple[int, str, str]]:
    """الحصول على الموظفين التابعين لمحافظة معينة"""
    try:
        response = supabase.table('Users').select('user_id, username, HealthAdministrations(admin_name)').eq('role', 'employee').eq('HealthAdministrations.governorate_id', governorate_id).execute()
        return [(item['user_id'], item['username'], item['HealthAdministrations']['admin_name']) 
                for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب موظفي المحافظة: {str(e)}")
        return []

def get_allowed_surveys(user_id: int) -> List[Tuple[int, str]]:
    """الحصول على الاستبيانات المسموح بها للموظف"""
    try:
        # الحصول على المحافظة التابعة للمستخدم
        response = supabase.table('Users').select('HealthAdministrations(governorate_id)').eq('user_id', user_id).execute()
        governorate_id = response.data[0]['HealthAdministrations']['governorate_id'] if response.data else None
        
        if not governorate_id:
            return []
            
        # الحصول على الاستبيانات المسموحة للمحافظة
        response = supabase.table('SurveyGovernorate').select('Surveys(survey_id, survey_name)').eq('governorate_id', governorate_id).execute()
        return [(item['Surveys']['survey_id'], item['Surveys']['survey_name']) 
                for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب الاستبيانات المسموح بها: {str(e)}")
        return []

def get_survey_fields(survey_id: int) -> List[Tuple[int, str, str, str, bool, int]]:
    """الحصول على حقول استبيان معين"""
    try:
        response = supabase.table('Survey_Fields').select('*').eq('survey_id', survey_id).order('field_order').execute()
        return [(item['field_id'], item['field_label'], item['field_type'], 
                item['field_options'], item['is_required'], item['field_order']) 
                for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب حقول الاستبيان: {str(e)}")
        return []

def get_user_allowed_surveys(user_id: int) -> List[Tuple[int, str]]:
    """الحصول على الاستبيانات المسموح بها للمستخدم"""
    try:
        response = supabase.table('UserSurveys').select('Surveys(survey_id, survey_name)').eq('user_id', user_id).execute()
        return [(item['Surveys']['survey_id'], item['Surveys']['survey_name']) 
                for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب الاستبيانات المسموح بها: {str(e)}")
        return []

def update_user_allowed_surveys(user_id: int, survey_ids: List[int]) -> bool:
    """تحديث الاستبيانات المسموح بها للمستخدم"""
    try:
        # حذف جميع التصاريح الحالية
        supabase.table('UserSurveys').delete().eq('user_id', user_id).execute()
        
        # إضافة التصاريح الجديدة
        for survey_id in survey_ids:
            supabase.table('UserSurveys').insert({
                'user_id': user_id,
                'survey_id': survey_id
            }).execute()
        
        return True
    except Exception as e:
        st.error(f"حدث خطأ في تحديث الاستبيانات المسموح بها: {str(e)}")
        return False

def get_response_details(response_id: int) -> List[Tuple[int, int, str, str, str, str]]:
    """الحصول على تفاصيل إجابة محددة"""
    try:
        response = supabase.table('Response_Details').select('detail_id, field_id, Survey_Fields(field_label, field_type, field_options), answer_value').eq('response_id', response_id).execute()
        return [(item['detail_id'], item['field_id'], 
                item['Survey_Fields']['field_label'], item['Survey_Fields']['field_type'],
                item['Survey_Fields']['field_options'], item['answer_value']) 
                for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب تفاصيل الإجابة: {str(e)}")
        return []

def update_response_detail(detail_id: int, new_value: str) -> bool:
    """تحديث قيمة إجابة محددة"""
    try:
        supabase.table('Response_Details').update({
            'answer_value': new_value
        }).eq('detail_id', detail_id).execute()
        return True
    except Exception as e:
        st.error(f"حدث خطأ في تحديث الإجابة: {str(e)}")
        return False

def get_response_info(response_id: int) -> Optional[Tuple[int, str, str, str, str, str]]:
    """الحصول على معلومات أساسية عن الإجابة"""
    try:
        response = supabase.table('Responses').select('response_id, Surveys(survey_name), Users(username), HealthAdministrations(admin_name, Governorates(governorate_name)), submission_date').eq('response_id', response_id).execute()
        if response.data:
            data = response.data[0]
            return (
                data['response_id'],
                data['Surveys']['survey_name'],
                data['Users']['username'],
                data['HealthAdministrations']['admin_name'],
                data['HealthAdministrations']['Governorates']['governorate_name'],
                data['submission_date']
            )
        return None
    except Exception as e:
        st.error(f"حدث خطأ في جلب معلومات الإجابة: {str(e)}")
        return None

def log_audit_action(user_id: int, action_type: str, table_name: str, 
                    record_id: int = None, old_value: Any = None, 
                    new_value: Any = None) -> bool:
    """تسجيل إجراء في سجل التعديلات"""
    try:
        supabase.table('AuditLog').insert({
            'user_id': user_id,
            'action_type': action_type,
            'table_name': table_name,
            'record_id': record_id,
            'old_value': json.dumps(old_value) if old_value else None,
            'new_value': json.dumps(new_value) if new_value else None
        }).execute()
        return True
    except Exception as e:
        st.error(f"حدث خطأ في تسجيل الإجراء: {str(e)}")
        return False

def get_audit_logs(table_name: str = None, action_type: str = None,
                  username: str = None, date_range: Tuple[str, str] = None,
                  search_query: str = None) -> List[Tuple[int, str, str, str, int, str, str, str]]:
    """الحصول على سجل التعديلات مع فلاتر متقدمة"""
    try:
        query = supabase.table('AuditLog').select('log_id, Users(username), action_type, table_name, record_id, old_value, new_value, action_timestamp')
        
        if table_name:
            query = query.eq('table_name', table_name)
        if action_type:
            query = query.eq('action_type', action_type)
        if username:
            query = query.ilike('Users.username', f'%{username}%')
        if date_range:
            query = query.gte('action_timestamp', date_range[0])
            query = query.lte('action_timestamp', date_range[1])
        if search_query:
            query = query.or_(f"old_value.ilike.%{search_query}%,new_value.ilike.%{search_query}%,Users.username.ilike.%{search_query}%,table_name.ilike.%{search_query}%,action_type.ilike.%{search_query}%")
            
        response = query.order('action_timestamp', desc=True).execute()
        return [(item['log_id'], item['Users']['username'], item['action_type'], 
                item['table_name'], item['record_id'], item['old_value'],
                item['new_value'], item['action_timestamp']) 
                for item in response.data]
    except Exception as e:
        st.error(f"حدث خطأ في جلب سجل التعديلات: {str(e)}")
        return []

def has_completed_survey_today(user_id: int, survey_id: int) -> bool:
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        response = supabase.table('Responses').select('*').eq('user_id', user_id).eq('survey_id', survey_id).eq('is_completed', True).gte('submission_date', f'{today}T00:00:00').lte('submission_date', f'{today}T23:59:59').execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False
