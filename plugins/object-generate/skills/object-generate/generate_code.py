#!/usr/bin/env python3
"""
Blogn Basic Object Generator

MySQL 데이터베이스 테이블로부터 기본 Java 객체(VO, EVO, DAO, Service 등)를 자동 생성합니다.
Java 원본 코드 구조를 그대로 따릅니다.
"""

import os
import sys
import shutil
import argparse
import random
import time
from typing import Dict, List, Tuple
import mysql.connector
from mysql.connector import Error

# 데이터베이스 설정 — 접속 정보는 환경변수로만 주입한다 (비밀번호/호스트 하드코딩 금지).
# 프로젝트별 값은 project.json 의 mysql 설정에서 읽어 스킬이 아래 env 로 전달한다.
DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', ''),
    'user': os.environ.get('MYSQL_USER', ''),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('BLOGN_DATABASE', '')
}

# 베이스 패키지 — 프로젝트별로 변경 가능.
# 우선순위: --package 인자 > BLOGN_BASE_PACKAGE 환경변수 > 기본값(com.softn.blogn)
BASE_PACKAGE = os.environ.get('BLOGN_BASE_PACKAGE', 'com.softn.blogn')

# BasicVO 속성 (EVO에서 제외할 필드들)
BASIC_VO_ATTRIBUTES = [
    'create_datetime', 'create_user_id', 'create_user_ip',
    'modify_datetime', 'modify_user_id', 'modify_user_ip', 'lock_timestamp'
]

# SQL 타입 -> Java 타입 매핑
TYPE_MAPPING = {
    'VARCHAR': 'String', 'CHAR': 'String', 'TEXT': 'String',
    'LONGTEXT': 'String', 'MEDIUMTEXT': 'String',
    'INT': 'Integer', 'BIGINT': 'Integer', 'TINYINT': 'Integer',
    'SMALLINT': 'Integer', 'NUMERIC': 'Integer',
    'DATETIME': 'Date', 'TIMESTAMP': 'Date', 'DATE': 'Date',
    'DECIMAL': 'Double', 'DOUBLE': 'Double', 'FLOAT': 'Float',
    'BIT': 'Boolean'
}


def get_db_connection():
    """MySQL 데이터베이스 연결을 생성합니다."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✓ MySQL 연결 성공: {DB_CONFIG['database']} (서버 버전: {db_info})")
            return connection
    except Error as e:
        print(f"✗ MySQL 연결 실패: {e}")
        sys.exit(1)


def snake_to_camel(snake_str: str, capitalize_first: bool = False) -> str:
    """snake_case를 camelCase로 변환합니다."""
    components = snake_str.split('_')
    if capitalize_first:
        return ''.join(x.title() for x in components)
    else:
        return components[0].lower() + ''.join(x.title() for x in components[1:])


def extract_module_and_entity(table_name: str) -> Tuple[str, str, str]:
    """테이블명에서 모듈명, 서브모듈명, 엔티티명을 추출합니다.

    2depth 이상의 테이블은 모두 2depth 패키지에 위치시킵니다.
    예: quz_show → sys.show
        quz_show_quiz → sys.show (같은 패키지)
    """
    parts = table_name.split('_')
    if len(parts) < 2:
        print(f"✗ 테이블명 형식 오류: {table_name} (모듈_엔티티 형식이어야 합니다)")
        sys.exit(1)

    module = parts[0].lower()
    # 2depth까지만 사용 (3depth 이상도 2depth 패키지로 통일)
    submodule = parts[1].lower()
    # 엔티티명은 전체 parts 사용 (ShowQuiz 형태)
    entity_parts = parts[1:]
    entity_name = ''.join([p.capitalize() for p in entity_parts])

    return module, submodule, entity_name


def get_table_info(connection, table_name: str) -> Dict:
    """테이블 정보를 조회합니다."""
    cursor = connection.cursor(dictionary=True)

    # 테이블 코멘트 조회
    query = """
        SELECT TABLE_COMMENT
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
    """
    cursor.execute(query, (DB_CONFIG['database'], table_name))
    result = cursor.fetchone()
    cursor.close()

    return {
        'table_comment': result['TABLE_COMMENT'] if result else table_name
    }


def get_table_schema(connection, table_name: str) -> List[Dict]:
    """테이블의 스키마 정보를 조회합니다."""
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_KEY,
            COLUMN_DEFAULT,
            EXTRA,
            COLUMN_COMMENT
        FROM
            INFORMATION_SCHEMA.COLUMNS
        WHERE
            TABLE_SCHEMA = %s
            AND TABLE_NAME = %s
        ORDER BY
            ORDINAL_POSITION
    """

    cursor.execute(query, (DB_CONFIG['database'], table_name))
    columns = cursor.fetchall()
    cursor.close()

    if not columns:
        print(f"✗ 테이블을 찾을 수 없습니다: {table_name}")
        sys.exit(1)

    return columns


def map_sql_type_to_java(sql_type: str) -> str:
    """SQL 타입을 Java 타입으로 매핑합니다."""
    return TYPE_MAPPING.get(sql_type.upper(), 'String')


def generate_serial_version_uid() -> str:
    """serialVersionUID를 생성합니다."""
    # 타임스탬프 기반으로 안전한 serialVersionUID 생성
    # Java 원본의 StringUtil.generateNewId와 유사한 방식
    timestamp_ms = int(time.time() * 1000)
    random_part = random.randint(0, 9999)

    # 타임스탬프 * 10000 + 랜덤값
    base_value = timestamp_ms * 10000 + random_part

    # 50% 확률로 음수로 변환 (Java long 범위 내에서)
    if random.random() < 0.5 and base_value < 9223372036854775807:
        value = -base_value
    else:
        value = base_value

    return str(value) + "L"


def get_gen_table_name(table_name: str) -> str:
    """테이블명을 PascalCase로 변환합니다."""
    parts = table_name.lower().split('_')
    return ''.join([p.capitalize() for p in parts])


def get_entity_name(column_name: str) -> str:
    """컬럼명을 camelCase로 변환합니다."""
    return snake_to_camel(column_name.lower(), False)


def generate_evo_class(module: str, submodule: str, entity_name: str, table_name: str, table_comment: str, columns: List[Dict]) -> str:
    """EVO 클래스 코드를 생성합니다."""

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service"
    class_name = get_gen_table_name(table_name) + "EVO"

    # Date import 필요 여부 확인
    needs_date_import = any(
        map_sql_type_to_java(col['DATA_TYPE']) == 'Date'
        for col in columns
        if col['COLUMN_NAME'].lower() not in BASIC_VO_ATTRIBUTES
    )

    code = f"""package {package};
"""

    if needs_date_import:
        code += "\nimport java.util.Date;\n"

    code += f"""
import {BASE_PACKAGE}.cmmn.vo.BasicVO;
    
import lombok.Getter;
import lombok.Setter;

/**
 * {table_comment}의 Entity 클래스
 *
 * @author SoftN Develop Center
 */
@Getter
@Setter
public class {class_name} extends BasicVO {{

    private static final long serialVersionUID = {generate_serial_version_uid()};
"""

    # BasicVO 속성을 제외한 컬럼 필드 생성
    for col in columns:
        column_name = col['COLUMN_NAME'].lower()
        if column_name not in BASIC_VO_ATTRIBUTES:
            java_field_name = get_entity_name(col['COLUMN_NAME'])
            java_type = map_sql_type_to_java(col['DATA_TYPE'])
            comment = col['COLUMN_COMMENT'] or col['COLUMN_NAME']

            code += f"    /** {comment} */\n"
            code += f"    private {java_type} {java_field_name};\n\n"

    code += "}\n"

    return code


def generate_vo_class(module: str, submodule: str, table_name: str, table_comment: str) -> str:
    """VO 클래스 코드를 생성합니다."""

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service"
    class_name = get_gen_table_name(table_name) + "VO"
    evo_class_name = get_gen_table_name(table_name) + "EVO"

    code = f"""package {package};

import lombok.Getter;
import lombok.Setter;

/**
 * {table_comment}의 Entity 구현 클래스
 *
 * @author SoftN Develop Center
 */
@Getter
@Setter
public class {class_name} extends {evo_class_name} {{

    private static final long serialVersionUID = {generate_serial_version_uid()};
}}
"""

    return code


def generate_service_interface(module: str, submodule: str, table_name: str, table_comment: str) -> str:
    """Service 인터페이스 코드를 생성합니다."""

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service"
    service_name = get_gen_table_name(table_name) + "Service"
    vo_name = get_gen_table_name(table_name) + "VO"
    param_vo_name = snake_to_camel(table_name, False) + "VO"

    code = f"""package {package};

import {BASE_PACKAGE}.cmmn.service.ProcessResultListVO;

/**
 * {table_comment}의 Service Interface 클래스
 *
 * @author SoftN Develop Center
 */
public interface {service_name} {{

    /**
     * {table_comment}의 전체 목록을 조회한다.
     * @param {param_vo_name}
     * @return ProcessResultListVO<{vo_name}>
     * @throws Exception
     */
    ProcessResultListVO<{vo_name}> list({vo_name}  {param_vo_name}) throws Exception;

    /**
     * {table_comment}의 페이징 목록을 조회한다.
     * @param {param_vo_name}
     * @param pageIndex
     * @param listScale
     * @param pageScale
     * @return ProcessResultListVO<{vo_name}>
     * @throws Exception
     */
    ProcessResultListVO<{vo_name}> listPageing({vo_name} {param_vo_name}, int pageIndex, int listScale, int pageScale) throws Exception;

    /**
     * {table_comment}의 상세 정보를 조회한다.
     * @param {param_vo_name}
     * @return {vo_name}
     * @throws Exception
     */
    {vo_name} view({vo_name} {param_vo_name}) throws Exception;

    /**
     * {table_comment}의 정보를 등록한다.
     * @param {param_vo_name}
     * @return String
     * @throws Exception
     */
    int create({vo_name} {param_vo_name}) throws Exception;

    /**
     * {table_comment}의 정보를 수정한다.
     * @param {param_vo_name}
     * @return String
     * @throws Exception
     */
    int modify({vo_name} {param_vo_name}) throws Exception;

    /**
     * {table_comment}의 정보를 삭제한다.
     * @param {param_vo_name}
     * @return String
     * @throws Exception
     */
    int remove({vo_name} {param_vo_name}) throws Exception;
}}
"""

    return code


def generate_service_impl(module: str, submodule: str, table_name: str, table_comment: str, has_lock_timestamp: bool = True) -> str:
    """ServiceImpl 클래스 코드를 생성합니다.

    has_lock_timestamp 가 False 이면(LOCK_TIMESTAMP 컬럼이 없는 테이블) modify/remove 에서
    낙관적 잠금(lockTimestamp) 비교 블록을 생성하지 않는다.
    """

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service.impl"
    service_name = get_gen_table_name(table_name) + "Service"
    service_impl_name = service_name + "Impl"
    vo_name = get_gen_table_name(table_name) + "VO"
    param_vo_name = snake_to_camel(table_name, False) + "VO"
    param_dao_name = snake_to_camel(table_name, False) + "Dao"
    dao_name = get_gen_table_name(table_name) + "GeneratedDAO"
    dao_bean_name = snake_to_camel(table_name, False) + "DAO"
    service_bean_name = snake_to_camel(table_name, False) + "Service"

    # LOCK_TIMESTAMP 컬럼이 있는 테이블만 낙관적 잠금 비교 블록을 생성한다.
    if has_lock_timestamp:
        lock_check = f"""        if (!originVO.getLockTimestamp().equals({param_vo_name}.getLockTimestamp())) {{
            throw new IllegalStateException("message.error.data.conflicted");
        }}
"""
        modify_comment = "        // lockTimestamp를 비교하여 수정 가능 여부를 판단\n"
        remove_comment = "        // lockTimestamp를 비교하여 삭제 가능 여부를 판단\n"
    else:
        lock_check = ""
        modify_comment = ""
        remove_comment = ""

    code = f"""package {package};

import java.util.List;

import jakarta.annotation.Resource;

import org.apache.log4j.Logger;
import org.egovframe.rte.fdl.cmmn.EgovAbstractServiceImpl;
import org.egovframe.rte.ptl.mvc.tags.ui.pagination.PaginationInfo;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import {BASE_PACKAGE}.cmmn.service.ProcessResultListVO;
import {BASE_PACKAGE}.{module}.{submodule}.service.{service_name};
import {BASE_PACKAGE}.{module}.{submodule}.service.{vo_name};

/**
 * {table_comment}의 ServiceImpl 클래스
 *
 * @author SoftN Develop Center
 */
@Service("{service_bean_name}")
public class {service_impl_name} extends EgovAbstractServiceImpl implements {service_name} {{

    private static final Logger log = Logger.getLogger({service_impl_name}.class);

    @Resource(name="{dao_bean_name}")
    private {dao_name}  {param_dao_name};

    /**
     * {table_comment}의 전체 목록을 조회한다.
     * @param {param_vo_name}
     * @return ProcessResultListVO<{vo_name}>
     * @throws Exception
     */
    @Override
    public ProcessResultListVO<{vo_name}> list({vo_name}  {param_vo_name}) throws Exception {{
        ProcessResultListVO<{vo_name}> resultList = new ProcessResultListVO<{vo_name}>();
        try{{
            List<{vo_name}> retList = {param_dao_name}.findList({param_vo_name});
            resultList.setReturnList(retList);
            resultList.setResult(1);
        }} catch (Exception e) {{
            log.error("{table_comment} 목록 조회 중 오류 발생", e);
            resultList.setResult(-1);
        }}
        return resultList;
    }}

    /**
     * {table_comment}의 페이징 목록을 조회한다.
     * @param {param_vo_name}
     * @param pageIndex
     * @param listScale
     * @param pageScale
     * @return ProcessResultListVO<{vo_name}>
     * @throws Exception
     */
    @Override
    public ProcessResultListVO<{vo_name}> listPageing({vo_name} {param_vo_name}, int pageIndex, int listScale, int pageScale) throws Exception {{
        ProcessResultListVO<{vo_name}> resultList = new ProcessResultListVO<{vo_name}>();
        try{{
            PaginationInfo paginationInfo = new PaginationInfo();
            paginationInfo.setCurrentPageNo(pageIndex);
            paginationInfo.setRecordCountPerPage(listScale);
            paginationInfo.setPageSize(pageScale);

            {param_vo_name}.setFirstIndex(paginationInfo.getFirstRecordIndex());
            {param_vo_name}.setListScale(listScale);

            int totalCount = {param_dao_name}.count({param_vo_name});
            paginationInfo.setTotalRecordCount(totalCount);

            List<{vo_name}> retList = {param_dao_name}.findPageingList({param_vo_name});
            resultList.setReturnList(retList);
            resultList.setPageInfo(paginationInfo);
            resultList.setResult(1);
        }} catch (Exception e) {{
            log.error("{table_comment} 페이징 목록 조회 중 오류 발생", e);
            resultList.setResult(-1);
        }}
        return resultList;
    }}

    /**
     * {table_comment}의 상세 정보를 조회한다.
     * @param {param_vo_name}
     * @return {vo_name}
     * @throws Exception
     */
    @Override
    public {vo_name} view({vo_name} {param_vo_name}) throws Exception {{
        return {param_dao_name}.findByPrimarykey({param_vo_name});
    }}

    /**
     * {table_comment}의 정보를 등록한다.
     * @param {param_vo_name}
     * @return String
     * @throws Exception
     */
    @Transactional
    @Override
    public int create({vo_name} {param_vo_name}) throws Exception {{
        return {param_dao_name}.insert({param_vo_name});
    }}

    /**
     * {table_comment}의 정보를 수정한다.
     * @param {param_vo_name}
     * @return String
     * @throws Exception
     */
    @Transactional
    @Override
    public int modify({vo_name} {param_vo_name}) throws Exception {{
{modify_comment}        {vo_name} originVO = {param_dao_name}.findByPrimarykey({param_vo_name});
        if (originVO == null) {{
            throw new IllegalArgumentException("message.error.data.not.found");
        }}
{lock_check}
        return {param_dao_name}.update({param_vo_name});
    }}

    /**
     * {table_comment}의 정보를 삭제한다.
     * @param {param_vo_name}
     * @return String
     * @throws Exception
     */
    @Transactional
    @Override
    public int remove({vo_name} {param_vo_name}) throws Exception {{
{remove_comment}        {vo_name} originVO = {param_dao_name}.findByPrimarykey({param_vo_name});
        if (originVO == null) {{
            throw new IllegalArgumentException("message.error.data.not.found");
        }}
{lock_check}
        return {param_dao_name}.delete({param_vo_name});
    }}
}}
"""

    return code


def generate_basic_dao(module: str, submodule: str, table_name: str, table_comment: str) -> str:
    """BasicDAO 클래스 코드를 생성합니다."""

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service.impl"
    dao_name = get_gen_table_name(table_name) + "BasicDAO"
    vo_name = get_gen_table_name(table_name) + "VO"
    param_vo_name = snake_to_camel(table_name, False) + "VO"

    code = f"""package {package};

import {BASE_PACKAGE}.cmmn.annotation.SetUserSession;
import {BASE_PACKAGE}.cmmn.dao.CustomAbstractDAO;
import {BASE_PACKAGE}.{module}.{submodule}.service.{vo_name};

/**
 * {table_comment}의 기본 CRUD를 처리 하는 DAO 클래스
 *
 * @author SoftN Develop Center
 */
public class {dao_name} extends CustomAbstractDAO {{

    /**
     * {table_comment}에서 Primary Key로 정보를 조회한다.
     * @param {param_vo_name}
     * @return {vo_name}
     * @throws Exception
     */
    public {vo_name} findByPrimarykey({vo_name} {param_vo_name}) throws Exception {{
        {vo_name} returnVO = ({vo_name})select("{dao_name}.findByPrimarykey", {param_vo_name});
         return returnVO;
    }}
    
    /**
     * {table_comment}에 정보를 등록한다.
     * @param {param_vo_name}
     * @return int
     * @throws Exception
     */
    @SetUserSession
    public int insert({vo_name} {param_vo_name}) throws Exception {{
         return insert("{dao_name}.insert",{param_vo_name});
    }}

    /**
     * {table_comment}의 정보를 수정한다.
     * @param {param_vo_name}
     * @return int
     * @throws Exception
     */
    @SetUserSession
    public int update({vo_name} {param_vo_name}) throws Exception {{
         return update("{dao_name}.update",{param_vo_name});
    }}

    /**
     * {table_comment}의 정보를 삭제한다.
     * @param {param_vo_name}
     * @return int
     * @throws Exception
     */
    public int delete({vo_name} {param_vo_name}) throws Exception {{
         return delete("{dao_name}.delete",{param_vo_name});
    }}

}}
"""

    return code


def generate_generated_dao(module: str, submodule: str, table_name: str, table_comment: str) -> str:
    """GeneratedDAO 클래스 코드를 생성합니다."""

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service.impl"
    dao_name = get_gen_table_name(table_name) + "GeneratedDAO"
    basic_dao_name = get_gen_table_name(table_name) + "BasicDAO"
    vo_name = get_gen_table_name(table_name) + "VO"
    param_vo_name = snake_to_camel(table_name, False) + "VO"
    dao_bean_name = snake_to_camel(table_name, False) + "DAO"

    code = f"""package {package};

import java.util.List;

import org.springframework.stereotype.Repository;

import {BASE_PACKAGE}.{module}.{submodule}.service.{vo_name};

/**
 * {table_comment}의 기본 CRUD 이외의 처리를 담당하는 DAO 클래스
 *
 * @author SoftN Develop Center
 */
@Repository("{dao_bean_name}")
public class {dao_name} extends {basic_dao_name} {{

    /**
     * {table_comment}의 전체 목록을 조회한다.
     *
     * @param {param_vo_name}
     * @return List<{vo_name}>
     * @throws Exception
     */
    public List<{vo_name}> findList({vo_name} {param_vo_name}) throws Exception {{
        return selectList("{dao_name}.findList", {param_vo_name});
    }}

    /**
     * {table_comment}의 카운트를 조회한다.
     *
     * @param {param_vo_name}
     * @return int
     * @throws Exception
     */
    public int count({vo_name} {param_vo_name}) throws Exception {{
        return (Integer)select("{dao_name}.count", {param_vo_name});
    }}

    /**
     * {table_comment}의 페이징 목록을 조회한다.
     *
     * @param {param_vo_name}
     * @return List<{vo_name}>
     * @throws Exception
     */
    public List<{vo_name}> findPageingList({vo_name} {param_vo_name}) throws Exception {{
        return selectList("{dao_name}.findPageingList", {param_vo_name});
    }}

    /**
     * {table_comment}의 신규 키값을 조회한다.
     *
     * @param {param_vo_name}
     * @return 직접 입력
     * @throws Exception
     */
    public int findKey({vo_name} {param_vo_name}) throws Exception {{
        return (Integer)select("{dao_name}.findKey", {param_vo_name});
    }}

}}
"""

    return code


def generate_basic_dao_sql(module: str, submodule: str, table_name: str, table_comment: str, columns: List[Dict]) -> str:
    """BasicDAO SQL 매핑 파일을 생성합니다."""

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service"
    dao_name = get_gen_table_name(table_name) + "BasicDAO"
    vo_name = get_gen_table_name(table_name) + "VO"
    param_vo_name = snake_to_camel(table_name, False) + "VO"
    full_vo_type = f"{package}.{vo_name}"

    # Primary key 찾기
    primary_keys = [col for col in columns if col['COLUMN_KEY'] == 'PRI']

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="{dao_name}">

    <select id="{dao_name}.findByPrimarykey" parameterType="{full_vo_type}" resultType="{full_vo_type}">
        /*
            SQL_ID : {dao_name}.findByPrimarykey
            설 명 : Primarykey로 단일 정보를 조회한다.
        */
        SELECT
"""

    # SELECT 컬럼
    for idx, col in enumerate(columns):
        column_name = col['COLUMN_NAME']
        field_name = get_entity_name(column_name)
        if idx == 0:
            xml += f"               {column_name} as {field_name} \n"
        else:
            xml += f"             , {column_name} as {field_name} \n"

    xml += f"""          FROM
               {table_name.upper()}
         WHERE
"""

    # WHERE 절
    for idx, pk in enumerate(primary_keys):
        column_name = pk['COLUMN_NAME']
        field_name = get_entity_name(column_name)
        if idx == 0:
            xml += f"               {column_name} = #{{{field_name}}} \n"
        else:
            xml += f"           AND {column_name} = #{{{field_name}}} \n"

    xml += f"""    </select>

    <insert id="{dao_name}.insert" parameterType="{full_vo_type}" >
        /*
            SQL ID : {dao_name}.insert
            설 명 : 단일행 정보를 등록합니다.
        */
        INSERT INTO {table_name.upper()} (
"""

    # INSERT 컬럼
    for idx, col in enumerate(columns):
        column_name = col['COLUMN_NAME']
        if idx == 0:
            xml += f"               {column_name} \n"
        else:
            xml += f"             , {column_name} \n"

    xml += "        ) VALUES ( \n"

    # VALUES
    for idx, col in enumerate(columns):
        column_name = col['COLUMN_NAME'].lower()
        field_name = get_entity_name(col['COLUMN_NAME'])

        if column_name in ['create_datetime', 'modify_datetime', 'lock_timestamp']:
            value = "now()"
        else:
            value = f"#{{{field_name}}}"

        if idx == 0:
            xml += f"               {value} \n"
        else:
            xml += f"             , {value} \n"

    xml += "        ) \n"
    xml += "    </insert> \n\n"

    # UPDATE
    xml += f"""    <update id="{dao_name}.update" parameterType="{full_vo_type}" >
        /*
            SQL ID : {dao_name}.update
            설 명 : 단일행 정보를 수정합니다.
        */
        UPDATE {table_name.upper()} SET
"""

    first_set = True
    for col in columns:
        column_name = col['COLUMN_NAME']
        column_name_lower = column_name.lower()
        field_name = get_entity_name(column_name)

        # PK는 제외
        if col['COLUMN_KEY'] == 'PRI':
            continue

        # APPEND 필드는 제외
        if column_name_lower in ['create_datetime', 'create_user_id', 'create_user_ip']:
            continue

        if column_name_lower in ['modify_datetime', 'lock_timestamp']:
            value = "now()"
        else:
            value = f"#{{{field_name}}}"

        if first_set:
            xml += f"               {column_name} = {value}\n"
            first_set = False
        else:
            xml += f"             , {column_name} = {value}\n"

    xml += "         WHERE \n"

    for idx, pk in enumerate(primary_keys):
        column_name = pk['COLUMN_NAME']
        field_name = get_entity_name(column_name)
        if idx == 0:
            xml += f"              {column_name} = #{{{field_name}}} \n"
        else:
            xml += f"          AND {column_name} = #{{{field_name}}} \n"

    xml += "    </update> \n\n"

    # DELETE
    xml += f"""    <delete id="{dao_name}.delete" parameterType="{full_vo_type}" >
        /*
            SQL ID : {dao_name}.delete
            설 명 : 단일행 정보를 삭제합니다.
        */
        DELETE FROM {table_name.upper()}
         WHERE
"""

    for idx, pk in enumerate(primary_keys):
        column_name = pk['COLUMN_NAME']
        field_name = get_entity_name(column_name)
        if idx == 0:
            xml += f"              {column_name} = #{{{field_name}}} \n"
        else:
            xml += f"          AND {column_name} = #{{{field_name}}} \n"

    xml += "    </delete> \n\n"
    xml += "</mapper>"

    return xml


def generate_generated_dao_sql(module: str, submodule: str, table_name: str, table_comment: str, columns: List[Dict]) -> str:
    """GeneratedDAO SQL 매핑 파일을 생성합니다."""

    package = f"{BASE_PACKAGE}.{module}.{submodule}.service"
    dao_name = get_gen_table_name(table_name) + "GeneratedDAO"
    vo_name = get_gen_table_name(table_name) + "VO"
    param_vo_name = snake_to_camel(table_name, False) + "VO"
    full_vo_type = f"{package}.{vo_name}"

    # Primary key 찾기 (WHERE 절용)
    primary_keys = [col for col in columns if col['COLUMN_KEY'] == 'PRI']

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="{dao_name}">

    <sql id="{dao_name}.selectQuery">
        <![CDATA[
        SELECT
"""

    for idx, col in enumerate(columns):
        column_name = col['COLUMN_NAME']
        field_name = get_entity_name(column_name)
        if idx == 0:
            xml += f"               A.{column_name} as {field_name} \n"
        else:
            xml += f"             , A.{column_name} as {field_name} \n"

    xml += f"""          FROM
               {table_name.upper()} A
        ]]>
    </sql>

    <sql id="{dao_name}.listFieldQuery">
        <![CDATA[
        SELECT @rownum := @rownum+1 as rowNum
"""

    for col in columns:
        column_name = col['COLUMN_NAME']
        field_name = get_entity_name(column_name)
        xml += f"             , A.{column_name} as {field_name} \n"

    xml += """        ]]>
    </sql>

"""

    xml += f"""    <sql id="{dao_name}.listFromQuery">
        <![CDATA[
          FROM
               {table_name.upper()} A, (SELECT @rownum:=0) TMP
        ]]>
    </sql>

    <sql id="{dao_name}.listWhereQuery">
        <![CDATA[
"""

    # WHERE 절 (복합키가 2개 이상인 경우, 마지막 키 제외하고 WHERE 생성)
    if len(primary_keys) > 2:
        xml += "         WHERE \n"
        for idx in range(len(primary_keys) - 1):
            pk = primary_keys[idx]
            column_name = pk['COLUMN_NAME']
            field_name = get_entity_name(column_name)
            if idx == 0:
                xml += f"               A.{column_name} = #{{{field_name}}} \n"
            else:
                xml += f"           AND A.{column_name} = #{{{field_name}}} \n"

    xml += """        ]]>
    </sql>

    <sql id=\"""" + dao_name + """.listOrderQuery">
        <![CDATA[
        ]]>
    </sql>

    <select id=\"""" + dao_name + """.findList" parameterType=\"""" + full_vo_type + """\" resultType=\"""" + full_vo_type + """\">
        /*
         SQL ID : """ + dao_name + """.findList
         설  명 : """ + table_comment + """의 전체 목록
        */
        <include refid=\"""" + dao_name + """.listFieldQuery"/>
        <include refid=\"""" + dao_name + """.listFromQuery"/>
        <include refid=\"""" + dao_name + """.listWhereQuery"/>
        <include refid=\"""" + dao_name + """.listOrderQuery"/>
    </select>

    <select id=\"""" + dao_name + """.findPageingList" parameterType=\"""" + full_vo_type + """\" resultType=\"""" + full_vo_type + """\">
        /*
         SQL ID : """ + dao_name + """.findPageingList
         설  명 : """ + table_comment + """의 페이징 목록
        */
        <include refid=\"""" + dao_name + """.listFieldQuery"/>
        <include refid=\"""" + dao_name + """.listFromQuery"/>
        <include refid=\"""" + dao_name + """.listWhereQuery"/>
        <include refid=\"""" + dao_name + """.listOrderQuery"/>
        LIMIT #{firstIndex}, #{listScale}
    </select>

    <select id=\"""" + dao_name + """.count" parameterType=\"""" + full_vo_type + """\" resultType="Integer">
        /*
         SQL ID : """ + dao_name + """.count
         설  명 : """ + table_comment + """의 검색 카운트
        */
        SELECT COUNT(*)
        <include refid=\"""" + dao_name + """.listFromQuery"/>
        <include refid=\"""" + dao_name + """.listWhereQuery"/>
    </select>

    <select id=\"""" + dao_name + """.findKey" parameterType=\"""" + full_vo_type + """\" resultType="Integer">
        /*
         SQL ID : """ + dao_name + """.findKey
         설  명 : """ + table_comment + """의 키 검색
        */
        -- 이곳의 쿼리는 직접 작성해야 합니다. parameterType과 resultType도 수정필요
    </select>
</mapper>
"""

    return xml


def generate_sql_map_config_snippet(module: str, submodule: str, table_name: str) -> str:
    """mybatis-config.xml에 추가할 스니펫을 생성합니다."""

    dao_name = get_gen_table_name(table_name)

    snippet = f"""    <!-- {dao_name} -->
    <mapper resource="com/sqlmap/mysql/module/{module}/{submodule}/{dao_name}BasicDAO_SQL.xml"/>
    <mapper resource="com/sqlmap/mysql/module/{module}/{submodule}/{dao_name}GeneratedDAO_SQL.xml"/>
"""

    return snippet


def save_file(file_path: str, content: str):
    """파일을 저장합니다."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ 생성: {file_path}")


def clean_output_dir(output_dir: str):
    """출력 디렉토리를 비웁니다. (존재하면 내부 파일/하위 디렉토리 모두 삭제)"""
    if not os.path.exists(output_dir):
        print(f"✓ 출력 디렉토리 신규 생성: {output_dir}\n")
        os.makedirs(output_dir, exist_ok=True)
        return

    if not os.path.isdir(output_dir):
        raise RuntimeError(f"출력 경로가 디렉토리가 아닙니다: {output_dir}")

    removed = 0
    for entry in os.listdir(output_dir):
        target = os.path.join(output_dir, entry)
        if os.path.isdir(target) and not os.path.islink(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        removed += 1
    print(f"✓ 출력 디렉토리 정리 완료: {output_dir} ({removed}개 항목 삭제)\n")


def generate_all_files(table_names: List[str], output_dir: str):
    """모든 파일을 생성합니다."""

    connection = get_db_connection()

    print(f"\n============================================================")
    print(f"Blogn Basic Object Generator")
    print(f"============================================================\n")
    print(f"✓ 생성할 테이블: {len(table_names)}개\n")

    all_snippets = []

    for table_name in table_names:
        print(f"[ {table_name} 처리 중... ]")

        # 테이블 정보 조회
        table_info = get_table_info(connection, table_name)
        table_comment = table_info['table_comment']

        # 테이블 스키마 조회
        columns = get_table_schema(connection, table_name)
        print(f"  ✓ 컬럼 수: {len(columns)}개")

        # 모듈명, 서브모듈명, 엔티티명 추출
        module, submodule, entity_name = extract_module_and_entity(table_name)
        print(f"  ✓ 모듈: {module}.{submodule}, 엔티티: {entity_name}")
        print(f"  ✓ 테이블 설명: {table_comment}")

        # 출력 디렉토리 설정
        java_service_dir = os.path.join(output_dir, "java", "com", "softn", "blogn", module, submodule, "service")
        java_impl_dir = os.path.join(output_dir, "java", "com", "softn", "blogn", module, submodule, "service", "impl")
        sqlmap_dir = os.path.join(output_dir, "resources", "com", "sqlmap", "mysql", "module", module, submodule)

        # Java 파일 생성
        evo_code = generate_evo_class(module, submodule, entity_name, table_name, table_comment, columns)
        save_file(os.path.join(java_service_dir, f"{get_gen_table_name(table_name)}EVO.java"), evo_code)

        vo_code = generate_vo_class(module, submodule, table_name, table_comment)
        save_file(os.path.join(java_service_dir, f"{get_gen_table_name(table_name)}VO.java"), vo_code)

        service_code = generate_service_interface(module, submodule, table_name, table_comment)
        save_file(os.path.join(java_service_dir, f"{get_gen_table_name(table_name)}Service.java"), service_code)

        has_lock_timestamp = any(col['COLUMN_NAME'].lower() == 'lock_timestamp' for col in columns)
        service_impl_code = generate_service_impl(module, submodule, table_name, table_comment, has_lock_timestamp)
        save_file(os.path.join(java_impl_dir, f"{get_gen_table_name(table_name)}ServiceImpl.java"), service_impl_code)

        basic_dao_code = generate_basic_dao(module, submodule, table_name, table_comment)
        save_file(os.path.join(java_impl_dir, f"{get_gen_table_name(table_name)}BasicDAO.java"), basic_dao_code)

        generated_dao_code = generate_generated_dao(module, submodule, table_name, table_comment)
        save_file(os.path.join(java_impl_dir, f"{get_gen_table_name(table_name)}GeneratedDAO.java"), generated_dao_code)

        # SQL 파일 생성
        basic_dao_sql = generate_basic_dao_sql(module, submodule, table_name, table_comment, columns)
        save_file(os.path.join(sqlmap_dir, f"{get_gen_table_name(table_name)}BasicDAO_SQL.xml"), basic_dao_sql)

        generated_dao_sql = generate_generated_dao_sql(module, submodule, table_name, table_comment, columns)
        save_file(os.path.join(sqlmap_dir, f"{get_gen_table_name(table_name)}GeneratedDAO_SQL.xml"), generated_dao_sql)

        # sql-map-config snippet
        snippet = generate_sql_map_config_snippet(module, submodule, table_name)
        all_snippets.append(snippet)

        print()

    # mybatis-config snippet 저장
    snippet_file = os.path.join(output_dir, 'resources', 'com', 'sqlmap', 'mysql', 'config', 'mybatis-config-snippet.xml')
    save_file(snippet_file, '\n'.join(all_snippets))

    print(f"============================================================")
    print(f"✓ 완료: {len(table_names)}개 테이블 처리 완료")
    print(f"✓ 출력 디렉토리: {output_dir}")
    print(f"============================================================\n")
    print(f"다음 단계:")
    print(f"1. 생성된 Java 파일을 src/main/java/{BASE_PACKAGE.replace(chr(46), chr(47))}/ 아래로 복사")
    print(f"2. 생성된 SQL 파일을 src/main/resources/com/sqlmap/mysql/module/ 아래로 복사")
    print(f"3. mybatis-config-snippet.xml의 내용을 mybatis-config.xml의 <mappers> 섹션에 추가")
    print(f"============================================================\n")

    connection.close()
    print("✓ 데이터베이스 연결 종료")


def main():
    """메인 함수"""
    global BASE_PACKAGE
    parser = argparse.ArgumentParser(description='Blogn Basic Object Generator')
    parser.add_argument('tables', nargs='+', help='테이블명 (1개 이상)')
    parser.add_argument('--output-dir', default='temp', help='출력 디렉토리 (기본: temp)')
    parser.add_argument('--no-clean', action='store_true',
                        help='출력 디렉토리를 비우지 않고 기존 파일 위에 생성합니다.')
    parser.add_argument('--package', default=None,
                        help='베이스 패키지 (미지정 시 BLOGN_BASE_PACKAGE 환경변수 또는 com.softn.blogn)')

    args = parser.parse_args()

    # 베이스 패키지 결정 (--package > 환경변수/기본값)
    if args.package:
        BASE_PACKAGE = args.package

    # 출력 디렉토리 절대 경로로 변환
    output_dir = os.path.abspath(args.output_dir)

    # 출력 디렉토리 정리 (기본 동작)
    if not args.no_clean:
        clean_output_dir(output_dir)
    else:
        print(f"✓ --no-clean 옵션: {output_dir} 를 비우지 않고 진행합니다.\n")

    # 파일 생성
    generate_all_files(args.tables, output_dir)


if __name__ == '__main__':
    main()
