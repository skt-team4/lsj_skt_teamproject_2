--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Homebrew)
-- Dumped by pg_dump version 16.9 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: analytics; Type: SCHEMA; Schema: -; Owner: isangjae
--

CREATE SCHEMA analytics;


ALTER SCHEMA analytics OWNER TO isangjae;

--
-- Name: chatbot; Type: SCHEMA; Schema: -; Owner: isangjae
--

CREATE SCHEMA chatbot;


ALTER SCHEMA chatbot OWNER TO isangjae;

--
-- Name: ml_features; Type: SCHEMA; Schema: -; Owner: isangjae
--

CREATE SCHEMA ml_features;


ALTER SCHEMA ml_features OWNER TO isangjae;

--
-- Name: btree_gin; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gin WITH SCHEMA public;


--
-- Name: EXTENSION btree_gin; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION btree_gin IS 'support for indexing common datatypes in GIN';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: interaction; Type: TYPE; Schema: public; Owner: isangjae
--

CREATE TYPE public.interaction AS ENUM (
    'text_input',
    'selection',
    'feedback',
    'coupon_use'
);


ALTER TYPE public.interaction OWNER TO isangjae;

--
-- Name: order_stat; Type: TYPE; Schema: public; Owner: isangjae
--

CREATE TYPE public.order_stat AS ENUM (
    'confirmed',
    'preparing',
    'prepared',
    'picked',
    'canceled'
);


ALTER TYPE public.order_stat OWNER TO isangjae;

--
-- Name: auto_delete_old_conversations(); Type: FUNCTION; Schema: public; Owner: isangjae
--

CREATE FUNCTION public.auto_delete_old_conversations() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM chatbot.conversations
    WHERE conversation_time < NOW() - INTERVAL '6 months';
END;
$$;


ALTER FUNCTION public.auto_delete_old_conversations() OWNER TO isangjae;

--
-- Name: clean_invalid_shop_references(); Type: FUNCTION; Schema: public; Owner: isangjae
--

CREATE FUNCTION public.clean_invalid_shop_references() RETURNS void
    LANGUAGE plpgsql
    AS $$
  BEGIN
      UPDATE chatbot.user_profiles
      SET favorite_shops = (
          SELECT array_agg(shop_id)
          FROM unnest(favorite_shops) as shop_id
          WHERE shop_id IN (SELECT id FROM chatbot.shops)
      );
  END;
  $$;


ALTER FUNCTION public.clean_invalid_shop_references() OWNER TO isangjae;

--
-- Name: get_shop_hours(integer, text); Type: FUNCTION; Schema: public; Owner: isangjae
--

CREATE FUNCTION public.get_shop_hours(shop_id integer, day_name text DEFAULT NULL::text) RETURNS TABLE(open_hour time without time zone, close_hour time without time zone)
    LANGUAGE plpgsql
    AS $$
  BEGIN
      RETURN QUERY
      SELECT
          (business_hours->COALESCE(day_name, to_char(NOW(), 'day'))->>'open')::TIME,
          (business_hours->COALESCE(day_name, to_char(NOW(), 'day'))->>'close')::TIME
      FROM chatbot.shops
      WHERE id = shop_id;
  END;
  $$;


ALTER FUNCTION public.get_shop_hours(shop_id integer, day_name text) OWNER TO isangjae;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: isangjae
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO isangjae;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: recommendations_log; Type: TABLE; Schema: analytics; Owner: isangjae
--

CREATE TABLE analytics.recommendations_log (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    shop_id integer NOT NULL,
    session_id uuid,
    time_stamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    request_food_type character varying(100),
    request_budget integer,
    request_location character varying(100),
    recommendations jsonb NOT NULL,
    recommendation_count integer NOT NULL,
    top_recommendation_shop_id integer,
    user_selection json,
    selection_timestamp timestamp without time zone,
    recommendation_method character varying(50),
    confidence_score numeric(4,3),
    wide_score numeric(4,3),
    deep_score numeric(4,3),
    rag_score numeric(4,3)
);


ALTER TABLE analytics.recommendations_log OWNER TO isangjae;

--
-- Name: recommendations_log_id_seq; Type: SEQUENCE; Schema: analytics; Owner: isangjae
--

ALTER TABLE analytics.recommendations_log ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME analytics.recommendations_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_feedback; Type: TABLE; Schema: analytics; Owner: isangjae
--

CREATE TABLE analytics.user_feedback (
    id bigint NOT NULL,
    session_id uuid,
    related_recommendation_id bigint,
    user_id integer NOT NULL,
    time_stamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    feedback_type character varying(30) NOT NULL,
    feedback_target_type character varying(30) NOT NULL,
    feedback_target_id character varying(30) NOT NULL,
    feedback_content jsonb,
    context jsonb
);


ALTER TABLE analytics.user_feedback OWNER TO isangjae;

--
-- Name: user_feedback_id_seq; Type: SEQUENCE; Schema: analytics; Owner: isangjae
--

ALTER TABLE analytics.user_feedback ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME analytics.user_feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: conversations; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
)
PARTITION BY RANGE (conversation_time);


ALTER TABLE chatbot.conversations OWNER TO isangjae;

--
-- Name: conversations_2024_08; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2024_08 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2024_08 OWNER TO isangjae;

--
-- Name: conversations_2024_09; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2024_09 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2024_09 OWNER TO isangjae;

--
-- Name: conversations_2024_10; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2024_10 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2024_10 OWNER TO isangjae;

--
-- Name: conversations_2024_11; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2024_11 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2024_11 OWNER TO isangjae;

--
-- Name: conversations_2024_12; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2024_12 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2024_12 OWNER TO isangjae;

--
-- Name: conversations_2025_01; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2025_01 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2025_01 OWNER TO isangjae;

--
-- Name: conversations_2025_02; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2025_02 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2025_02 OWNER TO isangjae;

--
-- Name: conversations_2025_03; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.conversations_2025_03 (
    id bigint NOT NULL,
    session_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    conversation_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    input_text character varying(1000) NOT NULL,
    response_text character varying(700) NOT NULL,
    extracted_intent character varying(50),
    intent_confidence numeric(4,3),
    emotion integer,
    extracted_entities jsonb,
    conversation_turn integer DEFAULT 1 NOT NULL,
    previous_intent character varying(50),
    user_strategy character varying(20),
    processing_time_ms integer,
    nlu_time_ms integer,
    rag_time_ms integer,
    response_time_ms integer,
    response_quality_score numeric(4,3),
    user_satisfaction_inferred numeric(4,3),
    conversation_coherence numeric(4,3),
    recommended_shop_ids integer[],
    selected_shop_id integer,
    applied_coupon_ids text[],
    CONSTRAINT conversations_extracted_intent_check CHECK (((extracted_intent)::text = ANY ((ARRAY['FOOD_REQUEST'::character varying, 'BUDGET_INQUIRY'::character varying, 'COUPON_INQUIRY'::character varying, 'LOCATION_INQUIRY'::character varying, 'TIME_INQUIRY'::character varying, 'GENERAL_CHAT'::character varying, 'MENU_OPTION'::character varying, 'EMERGENCY_FOOD'::character varying, 'GROUP_DINING'::character varying, 'BALANCE_CHECK'::character varying, 'BALANCE_CHARGE'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT conversations_intent_confidence_check CHECK (((intent_confidence >= (0)::numeric) AND (intent_confidence <= (1)::numeric))),
    CONSTRAINT conversations_user_strategy_check CHECK (((user_strategy)::text = ANY ((ARRAY['onboarding_mode'::character varying, 'data_building_mode'::character varying, 'normal_mode'::character varying, 'urgent_mode'::character varying])::text[])))
);


ALTER TABLE chatbot.conversations_2025_03 OWNER TO isangjae;

--
-- Name: conversations_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.conversations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.conversations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: coupons; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.coupons (
    id integer NOT NULL,
    coupon_name character varying(50) NOT NULL,
    coupon_code character varying(50) NOT NULL,
    coupon_description text,
    coupon_type character varying(30) NOT NULL,
    discount_amount integer,
    discount_rate numeric(3,2),
    max_discount_amount integer,
    min_order_amount integer DEFAULT 0,
    usage_type character varying(30) NOT NULL,
    target_categories text[],
    applicable_shop_ids integer[],
    target_user_types text[],
    valid_from date DEFAULT CURRENT_DATE NOT NULL,
    valid_until date NOT NULL,
    max_issue_count integer,
    max_use_per_user integer DEFAULT 1,
    total_issued integer DEFAULT 0,
    total_used integer DEFAULT 0,
    is_active boolean DEFAULT true NOT NULL,
    priority_score numeric(3,2) DEFAULT 0.50,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    created_by character varying(100),
    CONSTRAINT coupons_coupon_type_check CHECK (((coupon_type)::text = ANY ((ARRAY['FIXED_AMOUNT'::character varying, 'PERCENTAGE'::character varying, 'FREEBIE'::character varying, 'BOGO'::character varying])::text[]))),
    CONSTRAINT coupons_discount_amount_check CHECK ((discount_amount > 0)),
    CONSTRAINT coupons_discount_check CHECK ((((discount_amount IS NOT NULL) AND (discount_rate IS NULL)) OR ((discount_amount IS NULL) AND (discount_rate IS NOT NULL)))),
    CONSTRAINT coupons_discount_rate_check CHECK (((discount_rate > (0)::numeric) AND (discount_rate <= (1)::numeric))),
    CONSTRAINT coupons_priority_score_check CHECK (((priority_score >= (0)::numeric) AND (priority_score <= (1)::numeric))),
    CONSTRAINT coupons_usage_type_check CHECK (((usage_type)::text = ANY ((ARRAY['ALL'::character varying, 'SHOP'::character varying, 'CATEGORY'::character varying, 'FOODCARD'::character varying, 'NEW_USER'::character varying, 'LOYALTY'::character varying])::text[]))),
    CONSTRAINT coupons_valid_period CHECK (((valid_until IS NULL) OR (valid_until >= valid_from)))
);


ALTER TABLE chatbot.coupons OWNER TO isangjae;

--
-- Name: coupons_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.coupons ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.coupons_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: foodcard_users; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.foodcard_users (
    id integer NOT NULL,
    user_id integer NOT NULL,
    card_number character varying(30),
    card_type character varying(30) NOT NULL,
    card_status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    balance integer DEFAULT 0 NOT NULL,
    target_age_group character varying(20) NOT NULL,
    balance_alert_threshold integer DEFAULT 5000,
    balance_alert_sent boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    last_sync_at timestamp with time zone,
    CONSTRAINT foodcard_users_balance_check CHECK ((balance >= 0)),
    CONSTRAINT foodcard_users_card_status_check CHECK (((card_status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying, 'SUSPENDED'::character varying, 'EXPIRED'::character varying, 'LOST'::character varying])::text[]))),
    CONSTRAINT foodcard_users_card_type_check CHECK (((card_type)::text = ANY ((ARRAY['아동급식카드'::character varying, '청소년급식카드'::character varying, '취약계층지원카드'::character varying, '기타'::character varying])::text[]))),
    CONSTRAINT foodcard_users_target_age_group_check CHECK (((target_age_group)::text = ANY ((ARRAY['초등학생'::character varying, '중학생'::character varying, '고등학생'::character varying, '대학생'::character varying, '청년'::character varying, '기타'::character varying])::text[])))
);


ALTER TABLE chatbot.foodcard_users OWNER TO isangjae;

--
-- Name: foodcard_users_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.foodcard_users ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.foodcard_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: menus; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.menus (
    id integer NOT NULL,
    shop_id integer NOT NULL,
    menu_name character varying(50) NOT NULL,
    price integer NOT NULL,
    menu_description text,
    category character varying(30),
    options jsonb,
    is_available boolean DEFAULT true NOT NULL,
    is_best boolean DEFAULT false,
    dietary_info character varying(200),
    recommendation_frequency integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT menus_category_check CHECK (((category)::text = ANY ((ARRAY['메인메뉴'::character varying, '세트메뉴'::character varying, '사이드메뉴'::character varying, '음료'::character varying, '디저트'::character varying, '기타'::character varying])::text[]))),
    CONSTRAINT menus_price_check CHECK ((price >= 0)),
    CONSTRAINT menus_recommendation_frequency_check CHECK ((recommendation_frequency >= 0))
);


ALTER TABLE chatbot.menus OWNER TO isangjae;

--
-- Name: menus_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.menus ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.menus_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: orders; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.orders (
    id integer NOT NULL,
    user_id integer NOT NULL,
    shop_id integer NOT NULL,
    menu_id integer NOT NULL,
    order_status public.order_stat,
    order_time timestamp with time zone,
    quantity integer,
    price integer,
    discount_applied integer
);


ALTER TABLE chatbot.orders OWNER TO isangjae;

--
-- Name: orders_coupons; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.orders_coupons (
    order_id integer NOT NULL,
    user_wallet_id integer NOT NULL,
    applied_discount integer NOT NULL
);


ALTER TABLE chatbot.orders_coupons OWNER TO isangjae;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.orders ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: recent_conversations; Type: MATERIALIZED VIEW; Schema: chatbot; Owner: isangjae
--

CREATE MATERIALIZED VIEW chatbot.recent_conversations AS
 SELECT id,
    session_id,
    user_id,
    conversation_time,
    input_text,
    response_text,
    extracted_intent,
    intent_confidence,
    emotion,
    extracted_entities,
    conversation_turn,
    previous_intent,
    user_strategy,
    processing_time_ms,
    nlu_time_ms,
    rag_time_ms,
    response_time_ms,
    response_quality_score,
    user_satisfaction_inferred,
    conversation_coherence,
    recommended_shop_ids,
    selected_shop_id,
    applied_coupon_ids
   FROM chatbot.conversations
  WHERE (conversation_time > (CURRENT_TIMESTAMP - '7 days'::interval))
  WITH NO DATA;


ALTER MATERIALIZED VIEW chatbot.recent_conversations OWNER TO isangjae;

--
-- Name: reviews; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.reviews (
    id integer NOT NULL,
    user_id integer NOT NULL,
    shop_id integer NOT NULL,
    order_id integer NOT NULL,
    rating numeric(2,1) NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    sentiment character varying(20),
    quality_score numeric(3,2),
    helpful_count integer DEFAULT 0
);


ALTER TABLE chatbot.reviews OWNER TO isangjae;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.reviews ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.reviews_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: shops; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.shops (
    id integer NOT NULL,
    shop_name character varying(30) NOT NULL,
    category character varying(20) NOT NULL,
    address_name character varying(50),
    latitude numeric(8,6) NOT NULL,
    longitude numeric(9,6) NOT NULL,
    is_good_influence_shop boolean DEFAULT false,
    is_food_card_shop character(1) DEFAULT 'U'::bpchar NOT NULL,
    contact character varying(20),
    business_hours jsonb,
    current_status character varying(20) DEFAULT 'UNKNOWN'::character varying NOT NULL,
    popularity_score numeric(4,3) DEFAULT 0.000,
    quality_score numeric(4,3) DEFAULT 0.000,
    recommendation_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    data_from character varying(50) DEFAULT 'manual'::character varying,
    CONSTRAINT shops_category_check CHECK (((category)::text = ANY ((ARRAY['한식'::character varying, '중식'::character varying, '일식'::character varying, '양식'::character varying, '치킨'::character varying, '피자'::character varying, '패스트푸드'::character varying, '분식'::character varying, '카페/디저트'::character varying, '도시락/죽'::character varying, '프랜차이즈'::character varying, '기타음식'::character varying, '편의점'::character varying])::text[]))),
    CONSTRAINT shops_current_status_check CHECK (((current_status)::text = ANY ((ARRAY['OPEN'::character varying, 'CLOSED'::character varying, 'BREAK_TIME'::character varying, 'UNKNOWN'::character varying])::text[]))),
    CONSTRAINT shops_is_food_card_shop_check CHECK ((is_food_card_shop = ANY (ARRAY['Y'::bpchar, 'N'::bpchar, 'P'::bpchar, 'U'::bpchar]))),
    CONSTRAINT shops_location_check CHECK (((latitude >= ('-90'::integer)::numeric) AND (latitude <= (90)::numeric) AND (longitude >= ('-180'::integer)::numeric) AND (longitude <= (180)::numeric))),
    CONSTRAINT shops_popularity_score_check CHECK (((popularity_score >= (0)::numeric) AND (popularity_score <= (1)::numeric))),
    CONSTRAINT shops_quality_score_check CHECK (((quality_score >= (0)::numeric) AND (quality_score <= (1)::numeric))),
    CONSTRAINT shops_recommendation_count_check CHECK ((recommendation_count >= 0))
);


ALTER TABLE chatbot.shops OWNER TO isangjae;

--
-- Name: shops_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.shops ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.shops_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_profiles; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.user_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    preferred_categories text[] DEFAULT '{}'::text[],
    average_budget integer,
    favorite_shops integer[] DEFAULT '{}'::integer[],
    conversation_style character varying(20) DEFAULT 'friendly'::character varying,
    taste_preferences jsonb DEFAULT '{}'::jsonb,
    companion_patterns text[] DEFAULT '{}'::text[],
    location_preferences text[] DEFAULT '{}'::text[],
    good_influence_preference numeric(3,2) DEFAULT 0.50,
    interaction_count integer DEFAULT 0,
    data_completeness numeric(3,2) DEFAULT 0.00,
    recent_orders jsonb DEFAULT '[]'::jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_profiles_conversation_style_check CHECK (((conversation_style)::text = ANY ((ARRAY['friendly'::character varying, 'formal'::character varying, 'casual'::character varying, 'brief'::character varying])::text[]))),
    CONSTRAINT user_profiles_data_completeness_check CHECK (((data_completeness >= (0)::numeric) AND (data_completeness <= (1)::numeric))),
    CONSTRAINT user_profiles_good_influence_preference_check CHECK (((good_influence_preference >= (0)::numeric) AND (good_influence_preference <= (1)::numeric)))
);


ALTER TABLE chatbot.user_profiles OWNER TO isangjae;

--
-- Name: user_profiles_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.user_profiles ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.user_profiles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_wallet; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.user_wallet (
    id integer NOT NULL,
    user_id integer NOT NULL,
    coupon_id integer NOT NULL,
    coupon_status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    issued_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    issued_by character varying(100) DEFAULT 'SYSTEM'::character varying,
    acquisition_source character varying(50) NOT NULL,
    acquisition_context jsonb,
    expires_at timestamp with time zone,
    expiry_notified_at timestamp with time zone,
    expiry_notification_count integer DEFAULT 0,
    usage_probability numeric(4,3) DEFAULT 0.500,
    recommended_usage_date date,
    CONSTRAINT user_wallet_acquisition_source_check CHECK (((acquisition_source)::text = ANY ((ARRAY['WELCOME_BONUS'::character varying, 'LOYALTY_REWARD'::character varying, 'EMERGENCY_ASSIST'::character varying, 'PROMOTION'::character varying, 'ADMIN_GRANT'::character varying, 'REFERRAL'::character varying])::text[]))),
    CONSTRAINT user_wallet_coupon_status_check CHECK (((coupon_status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'USED'::character varying, 'EXPIRED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT user_wallet_usage_probability_check CHECK (((usage_probability >= (0)::numeric) AND (usage_probability <= (1)::numeric)))
);


ALTER TABLE chatbot.user_wallet OWNER TO isangjae;

--
-- Name: user_wallet_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.user_wallet ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.user_wallet_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: users; Type: TABLE; Schema: chatbot; Owner: isangjae
--

CREATE TABLE chatbot.users (
    id integer NOT NULL,
    external_user_id character varying(200) NOT NULL,
    platform character varying(50) DEFAULT 'web'::character varying NOT NULL,
    user_name character varying(30),
    nickname character varying(30),
    email character varying(100),
    phone_number character varying(20),
    birthday date,
    current_address text,
    preferred_location character varying(50),
    user_status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    last_login_at timestamp with time zone,
    CONSTRAINT users_email_format CHECK (((email)::text ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'::text)),
    CONSTRAINT users_platform_check CHECK (((platform)::text = ANY ((ARRAY['web'::character varying, 'mobile_app'::character varying, 'kakao'::character varying, 'line'::character varying, 'facebook'::character varying, 'test'::character varying])::text[]))),
    CONSTRAINT users_user_status_check CHECK (((user_status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying, 'SUSPENDED'::character varying, 'DELETED'::character varying])::text[])))
);


ALTER TABLE chatbot.users OWNER TO isangjae;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.users ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME chatbot.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: nlu_features; Type: TABLE; Schema: ml_features; Owner: isangjae
--

CREATE TABLE ml_features.nlu_features (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    nlu_intent character varying(50),
    nlu_confidence numeric(4,3),
    food_category_mentioned character varying(100),
    budget_mentioned integer,
    location_mentioned character varying(100),
    companions_mentioned json,
    time_preference character varying(50),
    menu_options json,
    special_requirements json,
    processing_time_ms integer,
    model_version character varying(20)
);


ALTER TABLE ml_features.nlu_features OWNER TO isangjae;

--
-- Name: nlu_features_id_seq; Type: SEQUENCE; Schema: ml_features; Owner: isangjae
--

ALTER TABLE ml_features.nlu_features ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME ml_features.nlu_features_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_interactions; Type: TABLE; Schema: ml_features; Owner: isangjae
--

CREATE TABLE ml_features.user_interactions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    session_id uuid,
    time_stamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    interaction_type public.interaction,
    food_preference_extracted character varying(100),
    budget_pattern_extracted integer,
    companion_pattern_extracted json,
    location_preference_extracted character varying(100),
    recommendation_provided boolean DEFAULT false,
    recommendation_count integer DEFAULT 0,
    recommendations jsonb,
    user_strategy character varying(30),
    conversation_turn integer
);


ALTER TABLE ml_features.user_interactions OWNER TO isangjae;

--
-- Name: user_interactions_id_seq; Type: SEQUENCE; Schema: ml_features; Owner: isangjae
--

ALTER TABLE ml_features.user_interactions ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME ml_features.user_interactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: conversations_2024_08; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2024_08 FOR VALUES FROM ('2024-08-01 00:00:00+09') TO ('2024-09-01 00:00:00+09');


--
-- Name: conversations_2024_09; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2024_09 FOR VALUES FROM ('2024-09-01 00:00:00+09') TO ('2024-10-01 00:00:00+09');


--
-- Name: conversations_2024_10; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2024_10 FOR VALUES FROM ('2024-10-01 00:00:00+09') TO ('2024-11-01 00:00:00+09');


--
-- Name: conversations_2024_11; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2024_11 FOR VALUES FROM ('2024-11-01 00:00:00+09') TO ('2024-12-01 00:00:00+09');


--
-- Name: conversations_2024_12; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2024_12 FOR VALUES FROM ('2024-12-01 00:00:00+09') TO ('2025-01-01 00:00:00+09');


--
-- Name: conversations_2025_01; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2025_01 FOR VALUES FROM ('2025-01-01 00:00:00+09') TO ('2025-02-01 00:00:00+09');


--
-- Name: conversations_2025_02; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2025_02 FOR VALUES FROM ('2025-02-01 00:00:00+09') TO ('2025-03-01 00:00:00+09');


--
-- Name: conversations_2025_03; Type: TABLE ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations ATTACH PARTITION chatbot.conversations_2025_03 FOR VALUES FROM ('2025-03-01 00:00:00+09') TO ('2025-04-01 00:00:00+09');


--
-- Data for Name: recommendations_log; Type: TABLE DATA; Schema: analytics; Owner: isangjae
--

COPY analytics.recommendations_log (id, user_id, shop_id, session_id, time_stamp, request_food_type, request_budget, request_location, recommendations, recommendation_count, top_recommendation_shop_id, user_selection, selection_timestamp, recommendation_method, confidence_score, wide_score, deep_score, rag_score) FROM stdin;
\.


--
-- Data for Name: user_feedback; Type: TABLE DATA; Schema: analytics; Owner: isangjae
--

COPY analytics.user_feedback (id, session_id, related_recommendation_id, user_id, time_stamp, feedback_type, feedback_target_type, feedback_target_id, feedback_content, context) FROM stdin;
\.


--
-- Data for Name: conversations_2024_08; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2024_08 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
1	98954bc1-16c1-42f8-ac21-4356f940ee2c	1	2024-08-15 10:30:00+09	오늘 점심 뭐 먹을까요?	김치찌개 어떠세요?	FOOD_REQUEST	0.950	\N	\N	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: conversations_2024_09; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2024_09 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
2	f1982e25-5040-4235-b0db-6adde79e95c6	1	2024-09-20 12:00:00+09	치킨 먹고 싶어요	최고 치킨을 추천드립니다!	FOOD_REQUEST	0.980	\N	\N	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: conversations_2024_10; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2024_10 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
3	4ec1098d-2f7e-455f-92c8-d34bc3e032d3	2	2024-10-10 18:30:00+09	저녁 추천해주세요	피자는 어떠신가요?	FOOD_REQUEST	0.920	\N	\N	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: conversations_2024_11; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2024_11 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
6	77f3a748-2a95-4122-abb6-419600cdf1e8	1	2024-11-15 10:00:00+09	오늘 점심 추천해주세요	김밥천국 어떠세요?	FOOD_REQUEST	\N	\N	{"meal_type": "lunch"}	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: conversations_2024_12; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2024_12 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
7	a0a79599-285c-42f9-884b-c5338a65a817	1	2024-12-01 18:00:00+09	급식카드 사용 가능한 곳	급식카드 사용 가능 가게입니다	COUPON_INQUIRY	\N	\N	{"card_type": "foodcard"}	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: conversations_2025_01; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2025_01 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
4	05d0963a-ad2e-4a22-88c2-4b333a4368d5	2	2025-01-15 13:00:00+09	급식카드 사용 가능한 곳 알려주세요	급식카드 사용 가능한 가게를 알려드릴게요.	COUPON_INQUIRY	0.890	\N	\N	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	{1,2}	\N	\N
8	4d253137-d186-4f03-812a-e11b0f1a0941	2	2025-01-10 12:00:00+09	1만원 이하 메뉴	예산에 맞는 메뉴입니다	BUDGET_INQUIRY	\N	\N	{"budget": 10000}	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: conversations_2025_02; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2025_02 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
5	13cfd58a-ed77-4ba7-921c-d0acb717ecd6	1	2025-02-20 14:30:00+09	1만원 이하 점심 추천	예산에 맞는 메뉴를 찾아드릴게요.	BUDGET_INQUIRY	0.930	\N	{"budget": 10000, "meal_type": "lunch"}	1	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: conversations_2025_03; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.conversations_2025_03 (id, session_id, user_id, conversation_time, input_text, response_text, extracted_intent, intent_confidence, emotion, extracted_entities, conversation_turn, previous_intent, user_strategy, processing_time_ms, nlu_time_ms, rag_time_ms, response_time_ms, response_quality_score, user_satisfaction_inferred, conversation_coherence, recommended_shop_ids, selected_shop_id, applied_coupon_ids) FROM stdin;
\.


--
-- Data for Name: coupons; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.coupons (id, coupon_name, coupon_code, coupon_description, coupon_type, discount_amount, discount_rate, max_discount_amount, min_order_amount, usage_type, target_categories, applicable_shop_ids, target_user_types, valid_from, valid_until, max_issue_count, max_use_per_user, total_issued, total_used, is_active, priority_score, created_at, created_by) FROM stdin;
\.


--
-- Data for Name: foodcard_users; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.foodcard_users (id, user_id, card_number, card_type, card_status, balance, target_age_group, balance_alert_threshold, balance_alert_sent, created_at, updated_at, last_sync_at) FROM stdin;
1	1	CARD-2024-001	청소년급식카드	ACTIVE	50000	고등학생	5000	f	2025-08-07 18:57:52.49777+09	2025-08-07 18:57:52.49777+09	\N
2	2	CARD-2024-002	아동급식카드	ACTIVE	30000	중학생	5000	f	2025-08-07 18:57:52.49777+09	2025-08-07 18:57:52.49777+09	\N
\.


--
-- Data for Name: menus; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.menus (id, shop_id, menu_name, price, menu_description, category, options, is_available, is_best, dietary_info, recommendation_frequency, created_at, updated_at) FROM stdin;
1	4	참치김밥	3500	\N	메인메뉴	{"size": [{"name": "보통", "price": 0}, {"name": "곱빼기", "price": 1000}]}	t	t	\N	0	2025-08-07 18:57:52.487411+09	2025-08-07 18:57:52.487411+09
2	4	라면	4000	\N	메인메뉴	{"spicy": [{"name": "순한맛", "price": 0}, {"name": "매운맛", "price": 0}]}	t	f	\N	0	2025-08-07 18:57:52.487411+09	2025-08-07 18:57:52.487411+09
3	5	아메리카노	4500	\N	음료	{"size": [{"name": "Tall", "price": 0}, {"name": "Grande", "price": 500}, {"name": "Venti", "price": 1000}]}	t	t	\N	0	2025-08-07 18:57:52.487411+09	2025-08-07 18:57:52.487411+09
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.orders (id, user_id, shop_id, menu_id, order_status, order_time, quantity, price, discount_applied) FROM stdin;
1	1	4	1	confirmed	2024-11-20 12:30:00+09	2	7000	1000
2	2	5	3	prepared	2024-11-20 13:00:00+09	1	4500	0
\.


--
-- Data for Name: orders_coupons; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.orders_coupons (order_id, user_wallet_id, applied_discount) FROM stdin;
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.reviews (id, user_id, shop_id, order_id, rating, comment, created_at, sentiment, quality_score, helpful_count) FROM stdin;
1	1	4	1	4.5	맛있고 양도 많아요! 급식카드 사용 가능해서 좋습니다.	2025-08-07 18:57:52.505557+09	\N	\N	0
2	2	5	2	3.0	평범한 맛이었어요.	2025-08-07 18:57:52.505557+09	\N	\N	0
\.


--
-- Data for Name: shops; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.shops (id, shop_name, category, address_name, latitude, longitude, is_good_influence_shop, is_food_card_shop, contact, business_hours, current_status, popularity_score, quality_score, recommendation_count, created_at, updated_at, data_from) FROM stdin;
1	맛있는 김치찌개	한식	\N	37.566500	126.978000	t	Y	\N	\N	UNKNOWN	0.000	0.000	0	2025-08-07 18:50:06.208053+09	2025-08-07 18:50:06.208053+09	manual
2	최고 치킨	치킨	\N	37.566600	126.978100	f	Y	\N	\N	UNKNOWN	0.000	0.000	0	2025-08-07 18:50:06.208053+09	2025-08-07 18:50:06.208053+09	manual
3	피자헛	피자	\N	37.566700	126.978200	f	N	\N	\N	UNKNOWN	0.000	0.000	0	2025-08-07 18:50:06.208053+09	2025-08-07 18:50:06.208053+09	manual
5	스타벅스	카페/디저트	\N	37.566600	126.978100	f	N	02-2345-6789	{"monday": {"open": "07:00", "close": "22:00"}, "saturday": {"open": "08:00", "close": "23:00"}}	UNKNOWN	0.000	0.000	0	2025-08-07 18:57:52.482678+09	2025-08-07 18:57:52.482678+09	manual
6	맥도날드	패스트푸드	\N	37.566700	126.978200	f	P	02-3456-7890	{"monday": {"open": "00:00", "close": "23:59"}}	UNKNOWN	0.000	0.000	0	2025-08-07 18:57:52.482678+09	2025-08-07 18:57:52.482678+09	manual
4	김밥천국	분식	\N	37.566500	126.978000	t	Y	02-1234-5678	{"monday": {"open": "08:00", "close": "22:00"}, "sunday": {"closed": true}, "tuesday": {"open": "08:00", "close": "22:00"}}	UNKNOWN	0.750	0.000	0	2025-08-07 18:57:52.482678+09	2025-08-07 18:57:52.490288+09	manual
\.


--
-- Data for Name: user_profiles; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.user_profiles (id, user_id, preferred_categories, average_budget, favorite_shops, conversation_style, taste_preferences, companion_patterns, location_preferences, good_influence_preference, interaction_count, data_completeness, recent_orders, created_at, updated_at) FROM stdin;
1	1	{한식,중식}	10000	{}	friendly	{"단맛": 0.3, "짠맛": 0.5, "매운맛": 0.8}	{}	{}	0.75	0	0.00	[]	2025-08-07 18:57:52.495381+09	2025-08-07 18:57:52.495381+09
2	2	{일식,양식}	20000	{}	friendly	{"단맛": 0.7, "매운맛": 0.2}	{}	{}	0.30	0	0.00	[]	2025-08-07 18:57:52.495381+09	2025-08-07 18:57:52.495381+09
\.


--
-- Data for Name: user_wallet; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.user_wallet (id, user_id, coupon_id, coupon_status, issued_at, issued_by, acquisition_source, acquisition_context, expires_at, expiry_notified_at, expiry_notification_count, usage_probability, recommended_usage_date) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: chatbot; Owner: isangjae
--

COPY chatbot.users (id, external_user_id, platform, user_name, nickname, email, phone_number, birthday, current_address, preferred_location, user_status, created_at, updated_at, last_login_at) FROM stdin;
1	test_user_001	test	테스트유저1	\N	test1@example.com	\N	\N	\N	\N	ACTIVE	2025-08-07 18:50:06.202277+09	2025-08-07 18:50:06.202277+09	\N
2	test_user_002	test	테스트유저2	\N	test2@example.com	\N	\N	\N	\N	ACTIVE	2025-08-07 18:50:06.202277+09	2025-08-07 18:50:06.202277+09	\N
4	line_user_456	line	이영희	영희	younghee@example.com	010-2345-6789	1995-08-20	\N	\N	ACTIVE	2025-08-07 18:57:52.473164+09	2025-08-07 18:57:52.473164+09	\N
5	web_user_789	web	박민수	민수	minsoo@example.com	010-3456-7890	1988-12-10	\N	\N	ACTIVE	2025-08-07 18:57:52.473164+09	2025-08-07 18:57:52.473164+09	\N
3	kakao_user_123	kakao	김철수	철수	chulsoo@example.com	010-1234-5678	1990-05-15	\N	강남구	ACTIVE	2025-08-07 18:57:52.473164+09	2025-08-07 18:57:52.477435+09	2025-08-07 18:57:52.477435+09
\.


--
-- Data for Name: nlu_features; Type: TABLE DATA; Schema: ml_features; Owner: isangjae
--

COPY ml_features.nlu_features (id, user_id, created_at, nlu_intent, nlu_confidence, food_category_mentioned, budget_mentioned, location_mentioned, companions_mentioned, time_preference, menu_options, special_requirements, processing_time_ms, model_version) FROM stdin;
\.


--
-- Data for Name: user_interactions; Type: TABLE DATA; Schema: ml_features; Owner: isangjae
--

COPY ml_features.user_interactions (id, user_id, session_id, time_stamp, interaction_type, food_preference_extracted, budget_pattern_extracted, companion_pattern_extracted, location_preference_extracted, recommendation_provided, recommendation_count, recommendations, user_strategy, conversation_turn) FROM stdin;
1	1	12345678-1234-1234-1234-123456789012	2025-08-07 19:08:45.286893	\N	\N	\N	\N	\N	f	0	\N	\N	\N
\.


--
-- Name: recommendations_log_id_seq; Type: SEQUENCE SET; Schema: analytics; Owner: isangjae
--

SELECT pg_catalog.setval('analytics.recommendations_log_id_seq', 1, false);


--
-- Name: user_feedback_id_seq; Type: SEQUENCE SET; Schema: analytics; Owner: isangjae
--

SELECT pg_catalog.setval('analytics.user_feedback_id_seq', 1, false);


--
-- Name: conversations_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.conversations_id_seq', 8, true);


--
-- Name: coupons_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.coupons_id_seq', 2, true);


--
-- Name: foodcard_users_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.foodcard_users_id_seq', 2, true);


--
-- Name: menus_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.menus_id_seq', 4, true);


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.orders_id_seq', 2, true);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.reviews_id_seq', 2, true);


--
-- Name: shops_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.shops_id_seq', 7, true);


--
-- Name: user_profiles_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.user_profiles_id_seq', 2, true);


--
-- Name: user_wallet_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.user_wallet_id_seq', 3, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: chatbot; Owner: isangjae
--

SELECT pg_catalog.setval('chatbot.users_id_seq', 5, true);


--
-- Name: nlu_features_id_seq; Type: SEQUENCE SET; Schema: ml_features; Owner: isangjae
--

SELECT pg_catalog.setval('ml_features.nlu_features_id_seq', 1, false);


--
-- Name: user_interactions_id_seq; Type: SEQUENCE SET; Schema: ml_features; Owner: isangjae
--

SELECT pg_catalog.setval('ml_features.user_interactions_id_seq', 1, true);


--
-- Name: recommendations_log recommendations_log_pkey; Type: CONSTRAINT; Schema: analytics; Owner: isangjae
--

ALTER TABLE ONLY analytics.recommendations_log
    ADD CONSTRAINT recommendations_log_pkey PRIMARY KEY (id);


--
-- Name: user_feedback user_feedback_pkey; Type: CONSTRAINT; Schema: analytics; Owner: isangjae
--

ALTER TABLE ONLY analytics.user_feedback
    ADD CONSTRAINT user_feedback_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2024_08 conversations_2024_08_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_08
    ADD CONSTRAINT conversations_2024_08_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations unique_session_id; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations
    ADD CONSTRAINT unique_session_id UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2024_08 conversations_2024_08_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_08
    ADD CONSTRAINT conversations_2024_08_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2024_09 conversations_2024_09_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_09
    ADD CONSTRAINT conversations_2024_09_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2024_09 conversations_2024_09_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_09
    ADD CONSTRAINT conversations_2024_09_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2024_10 conversations_2024_10_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_10
    ADD CONSTRAINT conversations_2024_10_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2024_10 conversations_2024_10_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_10
    ADD CONSTRAINT conversations_2024_10_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2024_11 conversations_2024_11_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_11
    ADD CONSTRAINT conversations_2024_11_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2024_11 conversations_2024_11_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_11
    ADD CONSTRAINT conversations_2024_11_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2024_12 conversations_2024_12_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_12
    ADD CONSTRAINT conversations_2024_12_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2024_12 conversations_2024_12_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2024_12
    ADD CONSTRAINT conversations_2024_12_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2025_01 conversations_2025_01_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2025_01
    ADD CONSTRAINT conversations_2025_01_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2025_01 conversations_2025_01_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2025_01
    ADD CONSTRAINT conversations_2025_01_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2025_02 conversations_2025_02_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2025_02
    ADD CONSTRAINT conversations_2025_02_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2025_02 conversations_2025_02_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2025_02
    ADD CONSTRAINT conversations_2025_02_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: conversations_2025_03 conversations_2025_03_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2025_03
    ADD CONSTRAINT conversations_2025_03_pkey PRIMARY KEY (id, conversation_time);


--
-- Name: conversations_2025_03 conversations_2025_03_session_id_conversation_time_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.conversations_2025_03
    ADD CONSTRAINT conversations_2025_03_session_id_conversation_time_key UNIQUE (session_id, conversation_time);


--
-- Name: coupons coupons_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.coupons
    ADD CONSTRAINT coupons_pkey PRIMARY KEY (id);


--
-- Name: foodcard_users foodcard_users_card_number_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.foodcard_users
    ADD CONSTRAINT foodcard_users_card_number_key UNIQUE (card_number);


--
-- Name: foodcard_users foodcard_users_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.foodcard_users
    ADD CONSTRAINT foodcard_users_pkey PRIMARY KEY (id);


--
-- Name: foodcard_users foodcard_users_unique_user; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.foodcard_users
    ADD CONSTRAINT foodcard_users_unique_user UNIQUE (user_id);


--
-- Name: menus menus_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.menus
    ADD CONSTRAINT menus_pkey PRIMARY KEY (id);


--
-- Name: orders_coupons orders_coupons_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.orders_coupons
    ADD CONSTRAINT orders_coupons_pkey PRIMARY KEY (order_id, user_wallet_id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: menus shop_menu_unique; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.menus
    ADD CONSTRAINT shop_menu_unique UNIQUE (shop_id, menu_name);


--
-- Name: shops shops_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.shops
    ADD CONSTRAINT shops_pkey PRIMARY KEY (id);


--
-- Name: reviews unique_user_order_review; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.reviews
    ADD CONSTRAINT unique_user_order_review UNIQUE (user_id, order_id);


--
-- Name: user_wallet user_coupon_unique_active; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.user_wallet
    ADD CONSTRAINT user_coupon_unique_active UNIQUE (user_id, coupon_id, coupon_status) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: user_profiles user_profiles_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.user_profiles
    ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (id);


--
-- Name: user_profiles user_profiles_unique_user; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.user_profiles
    ADD CONSTRAINT user_profiles_unique_user UNIQUE (user_id);


--
-- Name: user_wallet user_wallet_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.user_wallet
    ADD CONSTRAINT user_wallet_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_external_user_id_key; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.users
    ADD CONSTRAINT users_external_user_id_key UNIQUE (external_user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: nlu_features nlu_features_pkey; Type: CONSTRAINT; Schema: ml_features; Owner: isangjae
--

ALTER TABLE ONLY ml_features.nlu_features
    ADD CONSTRAINT nlu_features_pkey PRIMARY KEY (id);


--
-- Name: user_interactions user_interactions_pkey; Type: CONSTRAINT; Schema: ml_features; Owner: isangjae
--

ALTER TABLE ONLY ml_features.user_interactions
    ADD CONSTRAINT user_interactions_pkey PRIMARY KEY (id);


--
-- Name: idx_feedback_type; Type: INDEX; Schema: analytics; Owner: isangjae
--

CREATE INDEX idx_feedback_type ON analytics.user_feedback USING btree (feedback_type);


--
-- Name: idx_recommendation; Type: INDEX; Schema: analytics; Owner: isangjae
--

CREATE INDEX idx_recommendation ON analytics.user_feedback USING btree (related_recommendation_id);


--
-- Name: idx_recommendation_timestamp; Type: INDEX; Schema: analytics; Owner: isangjae
--

CREATE INDEX idx_recommendation_timestamp ON analytics.recommendations_log USING btree (user_id, time_stamp);


--
-- Name: idx_session_rmd; Type: INDEX; Schema: analytics; Owner: isangjae
--

CREATE INDEX idx_session_rmd ON analytics.recommendations_log USING btree (session_id);


--
-- Name: idx_shop_rmd; Type: INDEX; Schema: analytics; Owner: isangjae
--

CREATE INDEX idx_shop_rmd ON analytics.recommendations_log USING btree (top_recommendation_shop_id);


--
-- Name: idx_user_timestamp; Type: INDEX; Schema: analytics; Owner: isangjae
--

CREATE INDEX idx_user_timestamp ON analytics.user_feedback USING btree (user_id, time_stamp);


--
-- Name: idx_conversations_intent; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_conversations_intent ON ONLY chatbot.conversations USING btree (extracted_intent);


--
-- Name: conversations_2024_08_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_08_extracted_intent_idx ON chatbot.conversations_2024_08 USING btree (extracted_intent);


--
-- Name: idx_conversations_session; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_conversations_session ON ONLY chatbot.conversations USING btree (session_id);


--
-- Name: conversations_2024_08_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_08_session_id_idx ON chatbot.conversations_2024_08 USING btree (session_id);


--
-- Name: idx_conversations_user_time; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_conversations_user_time ON ONLY chatbot.conversations USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2024_08_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_08_user_id_conversation_time_idx ON chatbot.conversations_2024_08 USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2024_09_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_09_extracted_intent_idx ON chatbot.conversations_2024_09 USING btree (extracted_intent);


--
-- Name: conversations_2024_09_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_09_session_id_idx ON chatbot.conversations_2024_09 USING btree (session_id);


--
-- Name: conversations_2024_09_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_09_user_id_conversation_time_idx ON chatbot.conversations_2024_09 USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2024_10_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_10_extracted_intent_idx ON chatbot.conversations_2024_10 USING btree (extracted_intent);


--
-- Name: conversations_2024_10_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_10_session_id_idx ON chatbot.conversations_2024_10 USING btree (session_id);


--
-- Name: conversations_2024_10_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_10_user_id_conversation_time_idx ON chatbot.conversations_2024_10 USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2024_11_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_11_extracted_intent_idx ON chatbot.conversations_2024_11 USING btree (extracted_intent);


--
-- Name: conversations_2024_11_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_11_session_id_idx ON chatbot.conversations_2024_11 USING btree (session_id);


--
-- Name: conversations_2024_11_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_11_user_id_conversation_time_idx ON chatbot.conversations_2024_11 USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2024_12_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_12_extracted_intent_idx ON chatbot.conversations_2024_12 USING btree (extracted_intent);


--
-- Name: conversations_2024_12_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_12_session_id_idx ON chatbot.conversations_2024_12 USING btree (session_id);


--
-- Name: conversations_2024_12_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2024_12_user_id_conversation_time_idx ON chatbot.conversations_2024_12 USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2025_01_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_01_extracted_intent_idx ON chatbot.conversations_2025_01 USING btree (extracted_intent);


--
-- Name: conversations_2025_01_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_01_session_id_idx ON chatbot.conversations_2025_01 USING btree (session_id);


--
-- Name: conversations_2025_01_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_01_user_id_conversation_time_idx ON chatbot.conversations_2025_01 USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2025_02_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_02_extracted_intent_idx ON chatbot.conversations_2025_02 USING btree (extracted_intent);


--
-- Name: conversations_2025_02_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_02_session_id_idx ON chatbot.conversations_2025_02 USING btree (session_id);


--
-- Name: conversations_2025_02_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_02_user_id_conversation_time_idx ON chatbot.conversations_2025_02 USING btree (user_id, conversation_time DESC);


--
-- Name: conversations_2025_03_extracted_intent_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_03_extracted_intent_idx ON chatbot.conversations_2025_03 USING btree (extracted_intent);


--
-- Name: conversations_2025_03_session_id_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_03_session_id_idx ON chatbot.conversations_2025_03 USING btree (session_id);


--
-- Name: conversations_2025_03_user_id_conversation_time_idx; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX conversations_2025_03_user_id_conversation_time_idx ON chatbot.conversations_2025_03 USING btree (user_id, conversation_time DESC);


--
-- Name: idx_coupons_active; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_coupons_active ON chatbot.coupons USING btree (is_active, valid_from, valid_until);


--
-- Name: idx_coupons_categories; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_coupons_categories ON chatbot.coupons USING gin (target_categories);


--
-- Name: idx_coupons_code; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_coupons_code ON chatbot.coupons USING btree (coupon_code);


--
-- Name: idx_coupons_shops; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_coupons_shops ON chatbot.coupons USING gin (applicable_shop_ids);


--
-- Name: idx_coupons_type; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_coupons_type ON chatbot.coupons USING btree (usage_type);


--
-- Name: idx_foodcard_balance; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_foodcard_balance ON chatbot.foodcard_users USING btree (balance) WHERE (balance < 5000);


--
-- Name: idx_foodcard_status; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_foodcard_status ON chatbot.foodcard_users USING btree (card_status) WHERE ((card_status)::text = 'ACTIVE'::text);


--
-- Name: idx_menus_available; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_menus_available ON chatbot.menus USING btree (is_available) WHERE (is_available = true);


--
-- Name: idx_menus_best; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_menus_best ON chatbot.menus USING btree (is_best) WHERE (is_best = true);


--
-- Name: idx_menus_price; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_menus_price ON chatbot.menus USING btree (price);


--
-- Name: idx_menus_shop; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_menus_shop ON chatbot.menus USING btree (shop_id);


--
-- Name: idx_menus_shop_price; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_menus_shop_price ON chatbot.menus USING btree (shop_id, price);


--
-- Name: idx_orders_userid; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_orders_userid ON chatbot.orders USING btree (user_id);


--
-- Name: idx_recent_conversations_time; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_recent_conversations_time ON chatbot.recent_conversations USING btree (conversation_time);


--
-- Name: idx_reviews_order_rating; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_reviews_order_rating ON chatbot.reviews USING btree (order_id, rating);


--
-- Name: idx_reviews_user; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_reviews_user ON chatbot.reviews USING btree (user_id);


--
-- Name: idx_shops_category; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_shops_category ON chatbot.shops USING btree (category);


--
-- Name: idx_shops_food_card; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_shops_food_card ON chatbot.shops USING btree (is_food_card_shop) WHERE (is_food_card_shop <> 'N'::bpchar);


--
-- Name: idx_shops_good_influence; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_shops_good_influence ON chatbot.shops USING btree (is_good_influence_shop) WHERE (is_good_influence_shop = true);


--
-- Name: idx_shops_location; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_shops_location ON chatbot.shops USING btree (latitude, longitude);


--
-- Name: idx_shops_name_gin; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_shops_name_gin ON chatbot.shops USING gin (shop_name public.gin_trgm_ops);


--
-- Name: idx_shops_popularity; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_shops_popularity ON chatbot.shops USING btree (popularity_score DESC);


--
-- Name: idx_shops_status; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_shops_status ON chatbot.shops USING btree (current_status) WHERE ((current_status)::text = 'OPEN'::text);


--
-- Name: idx_user_coupon_expires; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_user_coupon_expires ON chatbot.user_wallet USING btree (expires_at) WHERE ((coupon_status)::text = 'ACTIVE'::text);


--
-- Name: idx_user_coupon_usage_prob; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_user_coupon_usage_prob ON chatbot.user_wallet USING btree (usage_probability DESC) WHERE ((coupon_status)::text = 'ACTIVE'::text);


--
-- Name: idx_user_coupon_user_status; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_user_coupon_user_status ON chatbot.user_wallet USING btree (user_id, coupon_status);


--
-- Name: idx_user_profiles_categories; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_user_profiles_categories ON chatbot.user_profiles USING gin (preferred_categories);


--
-- Name: idx_user_profiles_completeness; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_user_profiles_completeness ON chatbot.user_profiles USING btree (data_completeness DESC) WHERE (data_completeness > 0.5);


--
-- Name: idx_user_profiles_favorites; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_user_profiles_favorites ON chatbot.user_profiles USING gin (favorite_shops);


--
-- Name: idx_user_profiles_user; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_user_profiles_user ON chatbot.user_profiles USING btree (user_id);


--
-- Name: idx_users_external_id; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_users_external_id ON chatbot.users USING btree (external_user_id);


--
-- Name: idx_users_platform; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_users_platform ON chatbot.users USING btree (platform);


--
-- Name: idx_users_status; Type: INDEX; Schema: chatbot; Owner: isangjae
--

CREATE INDEX idx_users_status ON chatbot.users USING btree (user_status) WHERE ((user_status)::text = 'ACTIVE'::text);


--
-- Name: idx_food_category; Type: INDEX; Schema: ml_features; Owner: isangjae
--

CREATE INDEX idx_food_category ON ml_features.nlu_features USING btree (food_category_mentioned);


--
-- Name: idx_intent; Type: INDEX; Schema: ml_features; Owner: isangjae
--

CREATE INDEX idx_intent ON ml_features.nlu_features USING btree (nlu_intent);


--
-- Name: idx_interaction_timestamp; Type: INDEX; Schema: ml_features; Owner: isangjae
--

CREATE INDEX idx_interaction_timestamp ON ml_features.user_interactions USING btree (user_id, time_stamp);


--
-- Name: idx_session; Type: INDEX; Schema: ml_features; Owner: isangjae
--

CREATE INDEX idx_session ON ml_features.user_interactions USING btree (session_id);


--
-- Name: idx_user_timestamp; Type: INDEX; Schema: ml_features; Owner: isangjae
--

CREATE INDEX idx_user_timestamp ON ml_features.nlu_features USING btree (user_id, created_at);


--
-- Name: conversations_2024_08_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2024_08_extracted_intent_idx;


--
-- Name: conversations_2024_08_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2024_08_pkey;


--
-- Name: conversations_2024_08_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2024_08_session_id_conversation_time_key;


--
-- Name: conversations_2024_08_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2024_08_session_id_idx;


--
-- Name: conversations_2024_08_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2024_08_user_id_conversation_time_idx;


--
-- Name: conversations_2024_09_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2024_09_extracted_intent_idx;


--
-- Name: conversations_2024_09_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2024_09_pkey;


--
-- Name: conversations_2024_09_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2024_09_session_id_conversation_time_key;


--
-- Name: conversations_2024_09_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2024_09_session_id_idx;


--
-- Name: conversations_2024_09_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2024_09_user_id_conversation_time_idx;


--
-- Name: conversations_2024_10_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2024_10_extracted_intent_idx;


--
-- Name: conversations_2024_10_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2024_10_pkey;


--
-- Name: conversations_2024_10_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2024_10_session_id_conversation_time_key;


--
-- Name: conversations_2024_10_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2024_10_session_id_idx;


--
-- Name: conversations_2024_10_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2024_10_user_id_conversation_time_idx;


--
-- Name: conversations_2024_11_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2024_11_extracted_intent_idx;


--
-- Name: conversations_2024_11_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2024_11_pkey;


--
-- Name: conversations_2024_11_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2024_11_session_id_conversation_time_key;


--
-- Name: conversations_2024_11_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2024_11_session_id_idx;


--
-- Name: conversations_2024_11_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2024_11_user_id_conversation_time_idx;


--
-- Name: conversations_2024_12_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2024_12_extracted_intent_idx;


--
-- Name: conversations_2024_12_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2024_12_pkey;


--
-- Name: conversations_2024_12_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2024_12_session_id_conversation_time_key;


--
-- Name: conversations_2024_12_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2024_12_session_id_idx;


--
-- Name: conversations_2024_12_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2024_12_user_id_conversation_time_idx;


--
-- Name: conversations_2025_01_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2025_01_extracted_intent_idx;


--
-- Name: conversations_2025_01_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2025_01_pkey;


--
-- Name: conversations_2025_01_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2025_01_session_id_conversation_time_key;


--
-- Name: conversations_2025_01_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2025_01_session_id_idx;


--
-- Name: conversations_2025_01_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2025_01_user_id_conversation_time_idx;


--
-- Name: conversations_2025_02_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2025_02_extracted_intent_idx;


--
-- Name: conversations_2025_02_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2025_02_pkey;


--
-- Name: conversations_2025_02_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2025_02_session_id_conversation_time_key;


--
-- Name: conversations_2025_02_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2025_02_session_id_idx;


--
-- Name: conversations_2025_02_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2025_02_user_id_conversation_time_idx;


--
-- Name: conversations_2025_03_extracted_intent_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_intent ATTACH PARTITION chatbot.conversations_2025_03_extracted_intent_idx;


--
-- Name: conversations_2025_03_pkey; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.conversations_pkey ATTACH PARTITION chatbot.conversations_2025_03_pkey;


--
-- Name: conversations_2025_03_session_id_conversation_time_key; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.unique_session_id ATTACH PARTITION chatbot.conversations_2025_03_session_id_conversation_time_key;


--
-- Name: conversations_2025_03_session_id_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_session ATTACH PARTITION chatbot.conversations_2025_03_session_id_idx;


--
-- Name: conversations_2025_03_user_id_conversation_time_idx; Type: INDEX ATTACH; Schema: chatbot; Owner: isangjae
--

ALTER INDEX chatbot.idx_conversations_user_time ATTACH PARTITION chatbot.conversations_2025_03_user_id_conversation_time_idx;


--
-- Name: foodcard_users update_foodcard_users_updated_at; Type: TRIGGER; Schema: chatbot; Owner: isangjae
--

CREATE TRIGGER update_foodcard_users_updated_at BEFORE UPDATE ON chatbot.foodcard_users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: menus update_menus_updated_at; Type: TRIGGER; Schema: chatbot; Owner: isangjae
--

CREATE TRIGGER update_menus_updated_at BEFORE UPDATE ON chatbot.menus FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: shops update_shops_updated_at; Type: TRIGGER; Schema: chatbot; Owner: isangjae
--

CREATE TRIGGER update_shops_updated_at BEFORE UPDATE ON chatbot.shops FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: user_profiles update_user_profiles_updated_at; Type: TRIGGER; Schema: chatbot; Owner: isangjae
--

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON chatbot.user_profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: chatbot; Owner: isangjae
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON chatbot.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: recommendations_log recommendations_log_shop_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: isangjae
--

ALTER TABLE ONLY analytics.recommendations_log
    ADD CONSTRAINT recommendations_log_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES chatbot.shops(id);


--
-- Name: user_feedback user_feedback_related_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: isangjae
--

ALTER TABLE ONLY analytics.user_feedback
    ADD CONSTRAINT user_feedback_related_recommendation_id_fkey FOREIGN KEY (related_recommendation_id) REFERENCES analytics.recommendations_log(id);


--
-- Name: user_feedback user_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: analytics; Owner: isangjae
--

ALTER TABLE ONLY analytics.user_feedback
    ADD CONSTRAINT user_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id);


--
-- Name: conversations conversations_selected_shop_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.conversations
    ADD CONSTRAINT conversations_selected_shop_id_fkey FOREIGN KEY (selected_shop_id) REFERENCES chatbot.shops(id);


--
-- Name: conversations conversations_user_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE chatbot.conversations
    ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id) ON DELETE CASCADE;


--
-- Name: foodcard_users foodcard_users_user_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.foodcard_users
    ADD CONSTRAINT foodcard_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id) ON DELETE CASCADE;


--
-- Name: menus menus_shop_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.menus
    ADD CONSTRAINT menus_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES chatbot.shops(id) ON DELETE CASCADE;


--
-- Name: orders_coupons orders_coupons_order_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.orders_coupons
    ADD CONSTRAINT orders_coupons_order_id_fkey FOREIGN KEY (order_id) REFERENCES chatbot.orders(id) ON DELETE CASCADE;


--
-- Name: orders_coupons orders_coupons_user_wallet_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.orders_coupons
    ADD CONSTRAINT orders_coupons_user_wallet_id_fkey FOREIGN KEY (user_wallet_id) REFERENCES chatbot.user_wallet(id) ON DELETE CASCADE;


--
-- Name: orders orders_menu_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.orders
    ADD CONSTRAINT orders_menu_id_fkey FOREIGN KEY (menu_id) REFERENCES chatbot.menus(id);


--
-- Name: orders orders_shop_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.orders
    ADD CONSTRAINT orders_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES chatbot.shops(id);


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id);


--
-- Name: reviews reviews_order_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.reviews
    ADD CONSTRAINT reviews_order_id_fkey FOREIGN KEY (order_id) REFERENCES chatbot.orders(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_shop_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.reviews
    ADD CONSTRAINT reviews_shop_id_fkey FOREIGN KEY (shop_id) REFERENCES chatbot.shops(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_user_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.reviews
    ADD CONSTRAINT reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id);


--
-- Name: user_profiles user_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.user_profiles
    ADD CONSTRAINT user_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id) ON DELETE CASCADE;


--
-- Name: user_wallet user_wallet_coupon_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.user_wallet
    ADD CONSTRAINT user_wallet_coupon_id_fkey FOREIGN KEY (coupon_id) REFERENCES chatbot.coupons(id) ON DELETE CASCADE;


--
-- Name: user_wallet user_wallet_user_id_fkey; Type: FK CONSTRAINT; Schema: chatbot; Owner: isangjae
--

ALTER TABLE ONLY chatbot.user_wallet
    ADD CONSTRAINT user_wallet_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id) ON DELETE CASCADE;


--
-- Name: user_interactions user_interactions_user_id_fkey; Type: FK CONSTRAINT; Schema: ml_features; Owner: isangjae
--

ALTER TABLE ONLY ml_features.user_interactions
    ADD CONSTRAINT user_interactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES chatbot.users(id);


--
-- Name: recent_conversations; Type: MATERIALIZED VIEW DATA; Schema: chatbot; Owner: isangjae
--

REFRESH MATERIALIZED VIEW chatbot.recent_conversations;


--
-- PostgreSQL database dump complete
--

