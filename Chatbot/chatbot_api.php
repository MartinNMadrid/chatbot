<?php

$knowledgeBaseFile = 'base_conocimiento.json';

$baseConocimiento = [];
if (file_exists($knowledgeBaseFile)) {
    $jsonContent = file_get_contents($knowledgeBaseFile);
    $baseConocimiento = json_decode($jsonContent, true);
    $jsonContent = trim($jsonContent);
	$jsonContent = preg_replace('/[\x00-\x1F\x80-\x9F]/u', '', $jsonContent);
    if (json_last_error() !== JSON_ERROR_NONE || !is_array($baseConocimiento)) {
        error_log("Error al decodificar base_conocimiento.json: " . json_last_error_msg());
        $baseConocimiento = [];
    }
} else {
    error_log("El archivo base_conocimiento.json no se encontró en: " . $knowledgeBaseFile);
}

function preprocessText($text) {
    $text = mb_strtolower($text, 'UTF-8');
    $text = preg_replace('/[^\p{L}\p{N}\s]/u', '', $text);
    return $text;
}

function detectIntentAndEntities($userQuestion, $knowledgeBase) {
    $bestMatch = [
        'intencion' => 'desconocida',
        'entidades' => [],
        'score' => 0,
        'matched_question' => ''
    ];

    $normalizedUserQuestion = preprocessText($userQuestion);
    $userWords = explode(' ', $normalizedUserQuestion);

    foreach ($knowledgeBase as $entry) {
        if (!is_array($entry) || !isset($entry['pregunta'])) {
            continue;
        }

        $kbQuestion = preprocessText($entry['pregunta']);
        $kbWords = explode(' ', $kbQuestion);

        $commonWords = array_intersect($userWords, $kbWords);
        $currentScore = count($commonWords) / (count($userWords) + count($kbWords) - count($commonWords) + 0.001);

        if ($currentScore > $bestMatch['score']) {
            $bestMatch['score'] = $currentScore;
            $bestMatch['intencion'] = $entry['intencion'] ?? 'desconocida';
            $bestMatch['matched_question'] = $entry['pregunta'];
            $bestMatch['entidades'] = $entry['entidad'] ?? [];
        }
    }

    $threshold = 0.3;
    if ($bestMatch['score'] < $threshold) {
        $bestMatch['intencion'] = 'desconocida';
        $bestMatch['entidades'] = [];
    }

    return $bestMatch;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    $userQuestionRaw = $input['pregunta'] ?? '';

    $userQuestionProcessed = preprocessText($userQuestionRaw);

    $detectionResult = detectIntentAndEntities($userQuestionProcessed, $baseConocimiento);

    $response = [
        'respuesta' => "Lo siento, no tengo esa respuesta en mi base de conocimiento. Por favor, contacta al soporte técnico.",
        'recomendaciones' => []
    ];

    $foundMatch = false;

    foreach ($baseConocimiento as $entry) {
        if (!is_array($entry)) {
            error_log("detectIntentAndEntities: entrada inválida en base de conocimiento");
            continue;
        }
    
        if (!isset($entry['pregunta'])) {
            continue;
        }
        if ($entry['intencion'] === $detectionResult['intencion'] && $detectionResult['intencion'] !== 'desconocida') {
             $response['respuesta'] = $entry['respuesta'];
             $foundMatch = true;
             break;
        }
    }

    if (!$foundMatch) {
        $recommendations = [];
        $tempRecommendations = [];

        foreach ($baseConocimiento as $entry) {
            $kbQuestionProcessed = preprocessText($entry['pregunta']);
            $similarity = 0;

            $normalizedUserQuestion = preprocessText($kbQuestionProcessed);
            $userWords = explode(' ', $normalizedUserQuestion);
            //$userWords = explode(' ', $userQuestionProcessed);
            $kbWords = explode(' ', $kbQuestionProcessed);
            $commonWords = array_intersect($userWords, $kbWords);
            if (count($userWords) > 0 || count($kbWords) > 0) {
                 $similarity = (count($commonWords) * 2) / (count($userWords) + count($kbWords));
            }

            if ($similarity >= 0.3 && $similarity < 0.9) { 
                $tempRecommendations[$entry['pregunta']] = $similarity;
            }
        }

        arsort($tempRecommendations);
        $recommendations = array_slice(array_keys($tempRecommendations), 0, 3);

        if (!empty($recommendations)) {
            $response['respuesta'] = "No encontré una respuesta exacta, pero quizás quisiste preguntar algo de esto:";
            $response['recomendaciones'] = $recommendations;
        }
    }

    header('Content-Type: application/json');
    echo json_encode($response, JSON_UNESCAPED_UNICODE);
    exit;
}
