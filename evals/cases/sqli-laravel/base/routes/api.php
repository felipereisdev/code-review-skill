<?php

use App\Http\Controllers\UserSearchController;
use Illuminate\Support\Facades\Route;

Route::get('/users/search', UserSearchController::class)->middleware('auth:sanctum');
